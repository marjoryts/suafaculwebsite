"""SuaFacul - Flask Application (Python port from PHP)"""
import os
import sys
import math
import json
import logging
from dotenv import load_dotenv
from flask import (Flask, render_template, request, session, redirect,
                   url_for, jsonify, send_from_directory, abort)

# Ensure project root is on path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, '.env'))

from database.init_db import init_db
from app.models.usuario import Usuario
from app.models.curso import Curso
from app.models.vestibular import Vestibular
from app.models.favorito import Favorito
from app.models.teste_vocacional import TesteVocacional
from app.models.faculdade import Faculdade
from app.services import emec_service
from app.services import vestibular_service
from app.services import oauth_service
from app.services import scheduler_service
from app.services import censo_service
from app.services import seed_service
from app.services import busca_service
from functools import wraps

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'public'),
            static_url_path='/static')

_secret_key = os.environ.get('FLASK_SECRET_KEY', '').strip()
if not _secret_key:
    app.logger.warning(
        "[app] FLASK_SECRET_KEY não definida no ambiente — usando uma chave "
        "de desenvolvimento insegura. Defina FLASK_SECRET_KEY no .env antes "
        "de ir para produção (ver .env.example)."
    )
    _secret_key = 'suafacul_secret_key_change_in_production'
app.secret_key = _secret_key

# Sessões expiram após um período de inatividade (evita sessões "eternas"
# e dá previsibilidade ao tratamento de "sessão expirada" no login OAuth).
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=7)

# Initialize DB on startup
init_db()

# Seed automático (instituições/cursos) se o banco estiver vazio e os
# arquivos existirem em data/seeds/ — ver app/services/seed_service.py.
# Idempotente (só age se a tabela estiver vazia), então é seguro rodar
# toda vez que o processo sobe, mesmo com o reloader do Flask.
seed_service.rodar_seed_automatico_se_necessario()

# Login com Google (fica desabilitado, sem quebrar o app, se não configurado)
oauth_service.init_app(app)

# Automação diária (vestibulares) — com debug=True o Flask sobe um processo
# "pai" (watcher) e um processo "filho" (o que realmente serve requisições,
# marcado por WERKZEUG_RUN_MAIN=true); sem essa checagem o scheduler
# iniciaria duas vezes e a rotina diária rodaria em duplicidade.
_debug_mode = os.environ.get('FLASK_DEBUG', '1') == '1'  # mesmo padrão usado no app.run() abaixo
app.config['DEBUG'] = _debug_mode
if not _debug_mode or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    scheduler_service.start(app)


@app.template_filter('data_br')
def _filtro_data_br(valor, com_hora=False):
    """'2026-09-23 10:24:00' / '2026-09-23' -> '23/09/2026' (ou com hora)."""
    if not valor:
        return ''
    from datetime import datetime
    texto = str(valor)
    for formato in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            d = datetime.strptime(texto[:19], formato)
            return d.strftime('%d/%m/%Y %H:%M' if com_hora else '%d/%m/%Y')
        except ValueError:
            continue
    return texto

@app.context_processor
def _injetar_ano_atual():
    from datetime import date
    return {'current_year': date.today().year}

# Usuário da sessão disponível em qualquer template (header com foto/nome)
@app.context_processor
def _injetar_usuario_sessao():
    usuario_sessao = None
    if 'user_id' in session:
        usuario_sessao = {
            'id': session.get('user_id'),
            'nome_usuario': session.get('username'),
            'email': session.get('email'),
            'tipo': session.get('tipo'),
            'avatar_url': session.get('avatar_url'),
        }
    return dict(usuario_sessao=usuario_sessao)

# ──────────────────────────────────────────────
# Controle de acesso
# ──────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
            return redirect(url_for('login'))
        if session.get('tipo') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso restrito a administradores.'}), 403
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrapper

# ──────────────────────────────────────────────
# Static pages
# ──────────────────────────────────────────────

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/cursos')
def cursos():
    return render_template('cursos.html')

@app.route('/faculdades')
def faculdades():
    return render_template('faculdades.html')

@app.route('/vestibulares')
def vestibulares():
    return render_template('vestibulares.html')

@app.route('/testevocacional')
def testevocacional():
    return render_template('testevocacional.html')

@app.route('/sobrenos')
def sobrenos():
    return render_template('sobrenos.html')

@app.route('/ajuda')
def ajuda():
    return render_template('ajuda.html')

@app.route('/favoritos')
def favoritos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('favoritos.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    usuario = Usuario().buscar_por_id(user_id)
    if not usuario:
        # Conta removida enquanto a sessão ainda existia.
        session.clear()
        return redirect(url_for('login'))
    favorito_model = Favorito()
    contagem = favorito_model.contar_por_tipo(user_id)
    stats_favoritos = {
        'cursos': contagem['curso'],
        'faculdades': contagem['faculdade'],
        'vestibulares': contagem['vestibular'],
    }
    testes = TesteVocacional().listar_por_usuario(user_id, limite=10)
    return render_template(
        'dashboard.html',
        usuario=usuario,
        stats_favoritos=stats_favoritos,
        favoritos_recentes=favorito_model.listar_por_usuario(user_id)[:6],
        proximas_provas=favorito_model.proximos_vestibulares(user_id, limite=4),
        testes_vocacionais=testes,
        ultimo_teste=testes[0] if testes else None,
    )

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ──────────────────────────────────────────────
# Login com Google (OAuth/OIDC)
# ──────────────────────────────────────────────

def _login_usuario_na_sessao(user):
    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['nome_usuario']
    session['email'] = user['email']
    session['tipo'] = user.get('tipo', 'aluno')
    session['avatar_url'] = user.get('avatar_url')


@app.route('/auth/google')
def auth_google():
    if not oauth_service.is_configured():
        app.logger.error("[auth] Tentativa de login com Google sem GOOGLE_CLIENT_ID/SECRET configurados.")
        return redirect(url_for('login', oauth_error='nao_configurado'))
    redirect_uri = os.environ.get('GOOGLE_CALLBACK_URL') or url_for('auth_google_callback', _external=True)
    try:
        return oauth_service.google_client().authorize_redirect(redirect_uri)
    except Exception:
        app.logger.exception("[auth] Falha ao iniciar redirecionamento para o Google")
        return redirect(url_for('login', oauth_error='comunicacao'))


@app.route('/auth/google/callback')
def auth_google_callback():
    if not oauth_service.is_configured():
        return redirect(url_for('login', oauth_error='nao_configurado'))

    # Usuário cancelou o consentimento no Google (?error=access_denied&...)
    erro_google = request.args.get('error')
    if erro_google:
        app.logger.info("[auth] Login com Google cancelado/negado: %s", erro_google)
        return redirect(url_for('login', oauth_error='cancelado'))

    google = oauth_service.google_client()
    try:
        token = google.authorize_access_token()
    except Exception as e:
        # Cobre: state/CSRF inválido (ex.: sessão expirou entre o redirect e
        # o callback), falha de rede com o Google, resposta inesperada etc.
        app.logger.warning("[auth] Falha ao trocar código por token com o Google: %s", e)
        msg = 'sessao_expirada' if 'state' in str(e).lower() or 'csrf' in str(e).lower() else 'comunicacao'
        return redirect(url_for('login', oauth_error=msg))

    try:
        userinfo = token.get('userinfo') or google.parse_id_token(token)
    except Exception:
        app.logger.exception("[auth] Falha ao validar id_token do Google")
        return redirect(url_for('login', oauth_error='token_invalido'))

    if not userinfo or not userinfo.get('email'):
        app.logger.warning("[auth] Resposta do Google sem e-mail utilizável: %s", userinfo)
        return redirect(url_for('login', oauth_error='sem_email'))

    email = userinfo['email'].strip().lower()
    email_verificado = bool(userinfo.get('email_verified', True))
    google_id = userinfo.get('sub')
    nome = userinfo.get('name') or email.split('@')[0]
    avatar_url = userinfo.get('picture')

    usuario_model = Usuario()

    # 1) Já existe conta vinculada a este google_id -> login direto.
    usuario = usuario_model.buscar_por_google_id(google_id)
    if usuario:
        _login_usuario_na_sessao(usuario)
        return redirect(url_for('dashboard'))

    # 2) Já existe conta local com esse e-mail -> vincula (só quando o
    #    Google confirma que o e-mail é verificado, para não permitir que
    #    alguém sequestre uma conta existente com um e-mail não confirmado).
    usuario_existente = usuario_model.buscar_por_email(email)
    if usuario_existente:
        if not email_verificado:
            app.logger.warning("[auth] E-mail do Google não verificado, não vinculando: %s", email)
            return redirect(url_for('login', oauth_error='email_nao_verificado'))
        resultado = usuario_model.vincular_google(usuario_existente['id'], google_id, avatar_url)
        if not resultado.get('success'):
            app.logger.error("[auth] Falha ao vincular conta Google a usuário existente: %s", resultado.get('message'))
            return redirect(url_for('login', oauth_error='erro_interno'))
        _login_usuario_na_sessao(resultado['user'])
        return redirect(url_for('dashboard'))

    # 3) Não existe conta nenhuma -> cria uma nova conta 'aluno' via Google.
    resultado = usuario_model.criar_via_google(google_id, email, nome, avatar_url)
    if not resultado.get('success'):
        app.logger.error("[auth] Falha ao criar conta via Google: %s", resultado.get('message'))
        return redirect(url_for('login', oauth_error='erro_interno'))
    _login_usuario_na_sessao(resultado['user'])
    return redirect(url_for('dashboard'))

# ──────────────────────────────────────────────
# API — Usuário
# ──────────────────────────────────────────────

@app.route('/api/usuario/registrar', methods=['POST'])
def api_usuario_registrar():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not email or not password:
        return jsonify({'success': False, 'message': 'Por favor, preencha todos os campos.'})
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'success': False, 'message': 'Formato de e-mail inválido.'})
    return jsonify(Usuario().criar(username, email, password))

@app.route('/api/usuario/login', methods=['POST'])
def api_usuario_login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    if not username or not password:
        return jsonify({'success': False, 'message': 'Por favor, preencha todos os campos.'})
    result = Usuario().autenticar(username, password)
    if result['success']:
        _login_usuario_na_sessao(result['user'])
    return jsonify(result)

@app.route('/api/usuario/logout', methods=['POST', 'GET'])
def api_usuario_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/usuario/listar', methods=['GET'])
@admin_required
def api_usuario_listar():
    return jsonify({'success': True, 'usuarios': Usuario().listar()})

@app.route('/api/usuario/buscar', methods=['GET'])
def api_usuario_buscar():
    # Dados de conta: só o próprio usuário ou um administrador podem ver.
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    if str(id) != str(session['user_id']) and session.get('tipo') != 'admin':
        return jsonify({'success': False, 'message': 'Acesso restrito a administradores.'}), 403
    u = Usuario().buscar_por_id(id)
    if u:
        return jsonify({'success': True, 'usuario': u})
    return jsonify({'success': False, 'message': 'Usuário não encontrado.'})

@app.route('/api/usuario/atualizar', methods=['POST'])
@admin_required
def api_usuario_atualizar():
    id = request.form.get('id')
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip() or None
    if not id or not username or not email:
        return jsonify({'success': False, 'message': 'Dados obrigatórios não fornecidos.'})
    return jsonify(Usuario().atualizar(id, username, email, password))

@app.route('/api/usuario/perfil', methods=['POST'])
def api_usuario_perfil():
    """O usuário logado atualiza os PRÓPRIOS dados (nome de usuário, e-mail,
    senha). Não permite trocar o tipo de acesso nem editar outra conta — isso
    continua restrito a /api/usuario/atualizar e /definir-tipo (admin)."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirmacao = request.form.get('password_confirm', '')
    if not username or not email:
        return jsonify({'success': False, 'message': 'Nome de usuário e e-mail são obrigatórios.'})
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'success': False, 'message': 'Formato de e-mail inválido.'})
    if password:
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'A nova senha deve ter pelo menos 6 caracteres.'})
        if password != confirmacao:
            return jsonify({'success': False, 'message': 'A confirmação não confere com a nova senha.'})
    resultado = Usuario().atualizar(session['user_id'], username, email, password or None)
    if resultado.get('success'):
        session['username'] = username
        session['email'] = email
        resultado['message'] = 'Perfil atualizado com sucesso!'
    elif 'UNIQUE' in resultado.get('message', ''):
        resultado['message'] = 'Esse nome de usuário ou e-mail já está em uso.'
    return jsonify(resultado)

@app.route('/api/usuario/definir-tipo', methods=['POST'])
@admin_required
def api_usuario_definir_tipo():
    id = request.form.get('id')
    tipo = request.form.get('tipo', '').strip()
    if not id or not tipo:
        return jsonify({'success': False, 'message': 'Dados obrigatórios não fornecidos.'})
    if int(id) == session['user_id'] and tipo != 'admin':
        return jsonify({'success': False, 'message': 'Você não pode remover seu próprio acesso de admin.'})
    return jsonify(Usuario().definir_tipo(id, tipo))

@app.route('/api/usuario/deletar', methods=['POST'])
@admin_required
def api_usuario_deletar():
    id = request.form.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    if int(id) == session['user_id']:
        return jsonify({'success': False, 'message': 'Você não pode excluir seu próprio usuário.'})
    return jsonify(Usuario().deletar(id))

# ──────────────────────────────────────────────
# API — Cursos
# ──────────────────────────────────────────────

@app.route('/api/cursos/listar', methods=['GET'])
def api_cursos_listar():
    filtros = {}
    area = request.args.get('area', '')
    if area and area != 'Todas as áreas':
        filtros['area'] = area
    modalidade = request.args.getlist('modalidade')
    modalidade = [m for m in modalidade if m]
    if modalidade:
        filtros['modalidade'] = modalidade
    tipo_inst = request.args.getlist('tipo_instituicao')
    tipo_inst = [t for t in tipo_inst if t]
    if tipo_inst:
        filtros['tipo_instituicao'] = tipo_inst
    busca = request.args.get('busca', '')
    if busca:
        filtros['busca'] = busca
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    filtros['limit'] = limit
    filtros['offset'] = (page - 1) * limit
    model = Curso()
    cursos = model.listar(filtros)
    total = model.contar(filtros)
    return jsonify({'success': True, 'cursos': cursos, 'total': total,
                    'page': page, 'limit': limit,
                    'total_pages': math.ceil(total / limit) if limit else 1})

@app.route('/api/cursos/buscar', methods=['GET'])
def api_cursos_buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    c = Curso().buscar_por_id(id)
    if c:
        return jsonify({'success': True, 'curso': c})
    return jsonify({'success': False, 'message': 'Curso não encontrado.'})

@app.route('/api/cursos/sugestoes', methods=['GET'])
def api_cursos_sugestoes():
    """Autocomplete do campo 'curso' nas buscas (home e /faculdades):
    nomes de curso já cadastrados que começam com o termo digitado."""
    termo = request.args.get('q', '').strip()
    if len(termo) < 2:
        return jsonify({'sugestoes': []})
    sugestoes = Curso().sugestoes_por_nome(termo, limite=8)
    return jsonify({'sugestoes': sugestoes})

@app.route('/api/busca/sugestoes', methods=['GET'])
def api_busca_sugestoes():
    """Busca dinâmica do card de pesquisa (home e /faculdades): sugestões
    de localizações, faculdades e cursos que contêm o termo digitado
    (sem diferenciar acentos/maiúsculas), agrupadas por tipo.

    Parâmetros: q (termo, mín. 2 caracteres), tipos (opcional, lista
    separada por vírgula: local,faculdade,curso), limite (por tipo, máx. 10)."""
    termo = request.args.get('q', '').strip()
    tipos = [t.strip() for t in request.args.get('tipos', '').split(',') if t.strip()]
    tipos = tipos or list(busca_service.TIPOS)
    try:
        limite = int(request.args.get('limite', busca_service.LIMITE_PADRAO))
    except ValueError:
        limite = busca_service.LIMITE_PADRAO
    resultados = busca_service.sugestoes(termo, tipos=tipos, limite=limite)
    total = sum(len(v) for v in resultados.values())
    return jsonify({'success': True, 'termo': termo, 'resultados': resultados, 'total': total})

@app.route('/api/cursos/criar', methods=['POST'])
@admin_required
def api_cursos_criar():
    dados = {k: request.form.get(k, '') for k in ['nome','instituicao','modalidade','descricao','duracao','grau','area','tipo_instituicao']}
    faculdade_id = request.form.get('faculdade_id')
    dados['faculdade_id'] = int(faculdade_id) if faculdade_id else None
    if not dados['nome'] or not dados['instituicao']:
        return jsonify({'success': False, 'message': 'Nome e instituição são obrigatórios.'})
    return jsonify(Curso().criar(dados))

# ──────────────────────────────────────────────
# API — Faculdades
# ──────────────────────────────────────────────

@app.route('/api/faculdades/listar', methods=['GET'])
def api_faculdades_listar():
    filtros = {}
    tipo_inst = request.args.get('tipo_instituicao', '')
    if tipo_inst:
        filtros['tipo_instituicao'] = tipo_inst
    uf = request.args.get('uf', '')
    if uf:
        filtros['uf'] = uf
    cidade = request.args.get('cidade', '')
    if cidade:
        filtros['cidade'] = cidade
    curso = request.args.get('curso', '')
    if curso:
        filtros['curso'] = curso
    modalidade = request.args.getlist('modalidade')
    modalidade = [m for m in modalidade if m]
    if modalidade:
        filtros['modalidade'] = modalidade
    busca = request.args.get('busca', '')
    if busca:
        filtros['busca'] = busca
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    filtros['limit'] = limit
    filtros['offset'] = (page - 1) * limit
    model = Faculdade()
    faculdades = model.listar(filtros)
    total = model.contar(filtros)
    return jsonify({'success': True, 'faculdades': faculdades, 'total': total,
                    'page': page, 'limit': limit,
                    'total_pages': math.ceil(total / limit) if limit else 1})

# ──────────────────────────────────────────────
# API própria (v1) — instituições de ensino superior
#
# Substitui a dependência de consultar o e-MEC em tempo real: o site (e
# qualquer consumidor externo) passa a consultar SEMPRE esta API, que lê
# do banco local. Os dados desse banco são alimentados periodicamente
# (upload manual do CSV oficial do MEC no admin — ver /admin — já que o
# e-MEC bloqueia downloads automatizados; ver README).
#
# Somente leitura, pública, sem autenticação — é um catálogo de dados
# públicos (mesmas instituições que qualquer um vê no e-MEC).
# ──────────────────────────────────────────────

def _instituicao_para_api(f):
    """Formato de saída estável da API — não expõe colunas internas
    (id numérico interno, fonte da importação) que não fazem sentido
    para quem consome a API de fora."""
    return {
        'codigo_emec': f.get('codigo_emec'),
        'nome': f.get('nome'),
        'sigla': f.get('sigla'),
        'organizacao_academica': f.get('organizacao_academica'),
        'tipo_instituicao': f.get('tipo_instituicao'),
        'situacao': f.get('situacao'),
        'cidade': f.get('cidade'),
        'uf': f.get('uf'),
        'endereco': f.get('endereco') or None,
        'telefone': f.get('telefone') or None,
        'email': f.get('email') or None,
        'url': f.get('url') or None,
        'total_cursos_cadastrados': f.get('total_cursos', 0),
    }


@app.route('/api/v1/instituicoes', methods=['GET'])
def api_v1_instituicoes_listar():
    """Lista instituições de ensino superior cadastradas na base local.

    Query params (todos opcionais):
      uf              — sigla da UF (ex.: SP)
      cidade          — filtro parcial por cidade
      tipo_instituicao— 'Pública' ou 'Privada'
      busca           — filtro parcial por nome/sigla/cidade
      page (padrão 1), limit (padrão 20, máximo 100)
    """
    filtros = {}
    for campo in ('uf', 'cidade', 'tipo_instituicao', 'busca'):
        valor = request.args.get(campo, '').strip()
        if valor:
            filtros[campo] = valor.upper() if campo == 'uf' else valor

    page = max(1, int(request.args.get('page', 1) or 1))
    limit = min(100, max(1, int(request.args.get('limit', 20) or 20)))
    filtros['limit'] = limit
    filtros['offset'] = (page - 1) * limit

    model = Faculdade()
    instituicoes = [_instituicao_para_api(f) for f in model.listar(filtros)]
    total = model.contar(filtros)

    return jsonify({
        'data': instituicoes,
        'meta': {
            'total': total, 'page': page, 'limit': limit,
            'total_pages': math.ceil(total / limit) if limit else 1,
        }
    })


@app.route('/api/v1/instituicoes/<codigo_emec>', methods=['GET'])
def api_v1_instituicao_detalhe(codigo_emec):
    """Detalhe de uma instituição pelo código e-MEC."""
    instituicao = Faculdade().buscar_por_codigo_emec(codigo_emec)
    if not instituicao:
        return jsonify({'error': 'Instituição não encontrada para este código e-MEC.'}), 404
    return jsonify({'data': _instituicao_para_api(instituicao)})


@app.route('/api/v1/instituicoes/<codigo_emec>/cursos', methods=['GET'])
def api_v1_instituicao_cursos(codigo_emec):
    """Lista os cursos de graduação de uma instituição (importados do
    Censo da Educação Superior/INEP — ver README)."""
    instituicao = Faculdade().buscar_por_codigo_emec(codigo_emec)
    if not instituicao:
        return jsonify({'error': 'Instituição não encontrada para este código e-MEC.'}), 404
    from config.database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT nome, modalidade, grau, area FROM cursos WHERE faculdade_id=? ORDER BY nome ASC", (instituicao['id'],))
    cursos = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'data': cursos, 'meta': {'total': len(cursos), 'instituicao': instituicao['nome']}})

@app.route('/api/faculdades/buscar', methods=['GET'])
def api_faculdades_buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    f = Faculdade().buscar_por_id(id)
    if f:
        return jsonify({'success': True, 'faculdade': f})
    return jsonify({'success': False, 'message': 'Faculdade não encontrada.'})

@app.route('/api/faculdades/criar', methods=['POST'])
@admin_required
def api_faculdades_criar():
    dados = {k: request.form.get(k, '').strip() for k in Faculdade.CAMPOS}
    if not dados['nome']:
        return jsonify({'success': False, 'message': 'Nome da faculdade é obrigatório.'})
    if not dados.get('fonte'):
        dados['fonte'] = 'manual'
    if not dados.get('codigo_emec'):
        dados['codigo_emec'] = None
    return jsonify(Faculdade().criar(dados))

@app.route('/api/faculdades/atualizar', methods=['POST'])
@admin_required
def api_faculdades_atualizar():
    id = request.form.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    dados = {k: request.form.get(k, '').strip() for k in Faculdade.CAMPOS if k in request.form}
    return jsonify(Faculdade().atualizar(id, dados))

@app.route('/api/faculdades/deletar', methods=['POST'])
@admin_required
def api_faculdades_deletar():
    id = request.form.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    return jsonify(Faculdade().deletar(id))

@app.route('/api/faculdades/emec/importar', methods=['POST'])
@admin_required
def api_faculdades_emec_importar():
    """Importa uma ou várias faculdades do e-MEC por código.
    Aceita 'codigo' (único) ou 'codigos' (vários, separados por vírgula)."""
    codigo = request.form.get('codigo', '').strip()
    codigos_raw = request.form.get('codigos', '').strip()
    if codigo:
        return jsonify(emec_service.importar_faculdade_por_codigo(codigo))
    if codigos_raw:
        codigos = [c.strip() for c in codigos_raw.split(',') if c.strip()]
        return jsonify({'success': True, 'relatorio': emec_service.importar_faculdades_em_lote(codigos)})
    return jsonify({'success': False, 'message': "Informe 'codigo' ou 'codigos' do e-MEC."})

@app.route('/api/faculdades/emec/importar-uf', methods=['POST'])
@admin_required
def api_faculdades_emec_importar_uf():
    """Importa TODAS as instituições em atividade de uma UF a partir do
    e-MEC (endpoint interno de consulta avançada). Operação síncrona que
    pode demorar alguns segundos a minutos dependendo da UF."""
    uf = request.form.get('uf', '').strip().upper()
    if not uf:
        return jsonify({'success': False, 'message': "Informe a UF (ex: 'SP')."})
    if uf not in emec_service.UFS_BRASIL:
        return jsonify({'success': False, 'message': f"UF inválida: {uf}"})
    return jsonify(emec_service.importar_todas_faculdades_por_uf(uf))

@app.route('/api/faculdades/emec/importar-csv', methods=['POST'])
@admin_required
def api_faculdades_emec_importar_csv():
    """Importa instituições a partir do CSV oficial de Dados Abertos do MEC
    enviado manualmente pelo admin — alternativa quando o download
    automático (servidor->MEC) é bloqueado pelo WAF do e-MEC."""
    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'success': False, 'message': 'Selecione o arquivo CSV.'})
    if not arquivo.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Envie um arquivo .csv (baixado de dadosabertos.mec.gov.br).'})
    try:
        conteudo = arquivo.read()
        tamanho_mb = len(conteudo) / (1024 * 1024)
        if tamanho_mb > 300:  # margem generosa; o objetivo é só barrar upload do arquivo errado por engano
            return jsonify({'success': False, 'message': f'Arquivo de {tamanho_mb:.1f}MB é maior do que o esperado — confirme que é o CSV de instituições (não outro dataset do INEP/MEC).'})
        resultado = emec_service.importar_instituicoes_de_csv_upload(conteudo)
        return jsonify(resultado)
    except Exception as e:
        app.logger.warning("[emec] Falha ao importar CSV enviado pelo admin: %s", e)
        return jsonify({'success': False, 'message': f'Falha ao processar o CSV: {e}'})

@app.route('/api/cursos/censo/importar-csv', methods=['POST'])
@admin_required
def api_cursos_censo_importar_csv():
    """Importa cursos de graduação a partir do CSV oficial
    MICRODADOS_CADASTRO_CURSOS_<ano>.CSV do Censo da Educação Superior
    (INEP), enviado manualmente pelo admin. Só importa cursos cuja
    instituição (CO_IES) já esteja cadastrada na base local — ver
    'Importar CSV oficial' de instituições antes desta importação.
    Arquivo pode ser grande (400+MB) — processado em streaming."""
    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'success': False, 'message': 'Selecione o arquivo CSV.'})
    if not arquivo.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Envie o arquivo MICRODADOS_CADASTRO_CURSOS_<ano>.CSV.'})
    try:
        resultado = censo_service.importar_cursos_de_csv_upload(arquivo.stream)
        return jsonify(resultado)
    except Exception as e:
        app.logger.warning("[censo] Falha ao importar cursos do Censo INEP: %s", e)
        return jsonify({'success': False, 'message': f'Falha ao processar o CSV: {e}'})

@app.route('/api/faculdades/emec/importar-brasil', methods=['POST'])
@admin_required
def api_faculdades_emec_importar_brasil():
    """Importa TODAS as instituições em atividade do Brasil inteiro,
    percorrendo as 27 UFs com intervalo entre requisições para não
    sobrecarregar o e-MEC. Operação longa (pode levar vários minutos)."""
    return jsonify(emec_service.importar_todas_faculdades_brasil())

# ──────────────────────────────────────────────
# API — Vestibulares (+ automação de validação)
# ──────────────────────────────────────────────

@app.route('/api/vestibulares/listar', methods=['GET'])
def api_vestibulares_listar():
    filtros = {}
    tipo_inst = request.args.get('tipo_instituicao', '')
    if tipo_inst:
        filtros['tipo_instituicao'] = tipo_inst
    regiao = request.args.get('regiao', '')
    if regiao:
        filtros['regiao'] = regiao
    busca = request.args.get('busca', '')
    if busca:
        filtros['busca'] = busca
    curso = request.args.get('curso', '')
    if curso:
        filtros['curso'] = curso
    meses = request.args.getlist('mes')
    if meses:
        filtros['meses'] = [int(m) for m in meses if m]
    if request.args.get('incluir_privados') != 'true':
        filtros['apenas_publicos'] = True
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    filtros['limit'] = limit
    filtros['offset'] = (page - 1) * limit
    model = Vestibular()
    vests = model.listar(filtros)
    total = model.contar(filtros)
    return jsonify({'success': True, 'vestibulares': vests, 'total': total,
                    'page': page, 'limit': limit,
                    'total_pages': math.ceil(total / limit) if limit else 1})

@app.route('/api/vestibulares/buscar', methods=['GET'])
def api_vestibulares_buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    v = Vestibular().buscar_por_id(id)
    if v:
        return jsonify({'success': True, 'vestibular': v})
    return jsonify({'success': False, 'message': 'Vestibular não encontrado.'})

@app.route('/api/vestibulares/criar', methods=['POST'])
@admin_required
def api_vestibulares_criar():
    dados = {k: request.form.get(k, '') for k in ['nome','instituicao','tipo_instituicao','cidade','regiao','periodo_inscricao','data_prova','descricao','link_edital']}
    if not dados['nome'] or not dados['instituicao']:
        return jsonify({'success': False, 'message': 'Nome e instituição são obrigatórios.'})
    return jsonify(Vestibular().criar(dados))

@app.route('/api/vestibulares/validar', methods=['GET', 'POST'])
@admin_required
def api_vestibulares_validar():
    """Automação: valida as datas dos vestibulares e confere se a instituição
    já está cadastrada em `faculdades`. GET faz só o relatório (dry-run);
    POST com aplicar=true grava status_validacao/cadastrado_ok/faculdade_id."""
    aplicar = request.values.get('aplicar', 'false').lower() == 'true'
    return jsonify(vestibular_service.validar_vestibulares(aplicar=aplicar))

# ──────────────────────────────────────────────
# API — Admin: dashboard de controle
# ──────────────────────────────────────────────

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    from config.database import get_connection
    conn = get_connection()
    c = conn.cursor()
    stats = {}
    c.execute("SELECT COUNT(*) FROM usuarios"); stats['total_usuarios'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='admin'"); stats['total_admins'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM cursos"); stats['total_cursos'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM faculdades"); stats['total_faculdades'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM faculdades WHERE fonte='emec'"); stats['faculdades_importadas_emec'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vestibulares"); stats['total_vestibulares'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vestibulares WHERE status_validacao='ativo'"); stats['vestibulares_ativos'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vestibulares WHERE cadastrado_ok=0"); stats['vestibulares_sem_faculdade'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vestibulares WHERE status_validacao='encerrado'"); stats['vestibulares_encerrados'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='aluno'"); stats['total_alunos'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM usuarios WHERE created_at >= datetime('now', '-30 days')"); stats['novos_usuarios_30d'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM favoritos"); stats['total_favoritos'] = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM teste_vocacional_resultados"); stats['total_testes_vocacionais'] = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT faculdade_id) FROM cursos WHERE faculdade_id IS NOT NULL"); stats['faculdades_com_cursos'] = c.fetchone()[0]
    c.execute("SELECT id, tipo, executado_em, sucesso, resumo FROM automacao_logs ORDER BY executado_em DESC, id DESC LIMIT 5")
    automacoes = []
    for r in c.fetchall():
        try:
            resumo = json.loads(r['resumo']) if r['resumo'] else None
        except ValueError:
            resumo = None
        automacoes.append({'id': r['id'], 'tipo': r['tipo'], 'executado_em': r['executado_em'],
                           'sucesso': bool(r['sucesso']), 'resumo': resumo})
    conn.close()
    return jsonify({'success': True, 'stats': stats, 'automacoes': automacoes})

# ──────────────────────────────────────────────
# API — Favoritos
# ──────────────────────────────────────────────

def _check_auth():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    return None

@app.route('/api/favoritos/adicionar', methods=['POST'])
def api_favoritos_adicionar():
    err = _check_auth()
    if err:
        return err
    tipo = request.form.get('tipo', '')
    item_id = int(request.form.get('item_id', 0))
    nome_item = request.form.get('nome_item', '')
    if not tipo or item_id <= 0 or not nome_item:
        return jsonify({'success': False, 'message': 'Dados incompletos.'})
    if tipo not in ['curso', 'vestibular', 'faculdade']:
        return jsonify({'success': False, 'message': 'Tipo inválido.'})
    return jsonify(Favorito().adicionar(session['user_id'], tipo, item_id, nome_item))

@app.route('/api/favoritos/remover', methods=['POST'])
def api_favoritos_remover():
    err = _check_auth()
    if err:
        return err
    tipo = request.form.get('tipo', '')
    item_id = int(request.form.get('item_id', 0))
    if not tipo or item_id <= 0:
        return jsonify({'success': False, 'message': 'Dados incompletos.'})
    if tipo not in ['curso', 'vestibular', 'faculdade']:
        return jsonify({'success': False, 'message': 'Tipo inválido.'})
    return jsonify(Favorito().remover(session['user_id'], tipo, item_id))

@app.route('/api/favoritos/listar', methods=['GET'])
def api_favoritos_listar():
    err = _check_auth()
    if err:
        return err
    tipo = request.args.get('tipo')
    return jsonify({'success': True, 'favoritos': Favorito().listar_por_usuario(session['user_id'], tipo)})

@app.route('/api/favoritos/verificar', methods=['GET'])
def api_favoritos_verificar():
    err = _check_auth()
    if err:
        return err
    tipo = request.args.get('tipo', '')
    item_id = int(request.args.get('item_id', 0))
    if not tipo or item_id <= 0:
        return jsonify({'success': False, 'message': 'Dados incompletos.'})
    return jsonify({'success': True, 'is_favorito': Favorito().verificar_favorito(session['user_id'], tipo, item_id)})

@app.route('/api/favoritos/listar-ids', methods=['GET'])
def api_favoritos_listar_ids():
    err = _check_auth()
    if err:
        return err
    tipo = request.args.get('tipo', '')
    if not tipo or tipo not in ['curso', 'vestibular', 'faculdade']:
        return jsonify({'success': False, 'message': 'Tipo inválido.'})
    return jsonify({'success': True, 'ids': Favorito().listar_ids_favoritos(session['user_id'], tipo)})

# ──────────────────────────────────────────────
# API — Teste Vocacional
# ──────────────────────────────────────────────

@app.route('/api/teste_vocacional/salvar', methods=['POST'])
def api_teste_vocacional_salvar():
    perfil_principal = request.form.get('perfil_principal', '')
    perfis_json = request.form.get('perfis_json', '{}')
    respostas_json = request.form.get('respostas_json')
    if not perfil_principal:
        return jsonify({'success': False, 'message': 'Perfil principal não informado.'})
    usuario_id = session.get('user_id')
    return jsonify(TesteVocacional().salvar_resultado({
        'usuario_id': usuario_id,
        'perfil_principal': perfil_principal,
        'perfis_json': perfis_json,
        'respostas_json': respostas_json
    }))

# ──────────────────────────────────────────────
# 404
# ──────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    print("SuaFacul rodando em http://localhost:5000")
    app.run(debug=_debug_mode, port=int(os.environ.get('PORT', 5000)))
