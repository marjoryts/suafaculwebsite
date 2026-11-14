"""Correções da auditoria técnica:

1. teste_vocacional_resultados.usuario_id → usuarios(id) ON DELETE SET NULL
   (excluir pelo admin um usuário que fez o teste não pode mais falhar com
   "FOREIGN KEY constraint failed") + migração de bancos existentes.
2. Remoção da tabela órfã vestibular_inscricoes.
4. Estatísticas do admin contam as duas origens do e-MEC.
5. Pontuação do teste vocacional com uma única implementação para Web e API.
"""
import itertools
import json
import random
import sqlite3

import pytest

from app.services import teste_vocacional_service as tvs
from app.services.teste_vocacional_dados import SECOES
from config.database import get_connection


PERGUNTAS = [p for s in SECOES for p in s['perguntas']]


def _bearer(client, login, senha):
    r = client.post('/api/v1/auth/login', json={'email': login, 'password': senha})
    assert r.status_code == 200, r.get_data(as_text=True)
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + r.get_json()['data']['tokens']['access_token']
    return client


def _sql(sql, params=()):
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _escrever(sql, params=()):
    conn = get_connection()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def _admin_id():
    return _sql("SELECT id FROM usuarios WHERE tipo='admin' ORDER BY id LIMIT 1")[0]['id']


def _aluno_com_testes(client, username='maria', email='maria@x.com', senha='segredo123', n=2):
    """Cria um aluno (sessão web), faz `n` testes logado e sai. Devolve o id."""
    r = client.post('/api/usuario/registrar', data={'username': username, 'email': email, 'password': senha})
    assert r.get_json()['success'] is True
    client.post('/api/usuario/login', data={'username': username, 'password': senha})
    for _ in range(n):
        r = client.post('/api/teste_vocacional/responder', data={p['id']: 'a' for p in PERGUNTAS})
        assert r.status_code == 200 and r.get_json()['salvo'] is True
    usuario_id = _sql("SELECT id FROM usuarios WHERE nome_usuario=?", (username,))[0]['id']
    client.post('/api/usuario/logout')
    return usuario_id


# ── 1. Exclusão de usuário com resultados do teste vocacional ──────────────

def test_admin_web_exclui_usuario_que_fez_o_teste_e_preserva_os_resultados(app, client):
    usuario_id = _aluno_com_testes(client)
    ids = [r['id'] for r in _sql("SELECT id FROM teste_vocacional_resultados WHERE usuario_id=?", (usuario_id,))]
    assert len(ids) == 2
    total_antes = _sql("SELECT COUNT(*) AS n FROM teste_vocacional_resultados")[0]['n']

    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    r = client.post('/api/usuario/deletar', data={'id': usuario_id})
    assert r.get_json()['success'] is True, r.get_json()

    assert _sql("SELECT id FROM usuarios WHERE id=?", (usuario_id,)) == []
    # Resultados preservados (histórico/estatística), sem vínculo com a pessoa.
    preservados = _sql(f"SELECT id, usuario_id, perfil_principal, perfis_json FROM teste_vocacional_resultados "
                       f"WHERE id IN ({','.join('?' * len(ids))})", ids)
    assert len(preservados) == 2
    assert all(p['usuario_id'] is None for p in preservados)
    assert all(p['perfil_principal'] == 'tecnico' and json.loads(p['perfis_json'])['scores'] for p in preservados)
    assert _sql("SELECT COUNT(*) AS n FROM teste_vocacional_resultados")[0]['n'] == total_antes
    # Estatística do painel continua contando os testes realizados.
    stats = client.get('/api/admin/stats').get_json()['stats']
    assert stats['total_testes_vocacionais'] == total_antes


def test_admin_api_v1_exclui_usuario_que_fez_o_teste(app):
    aluno = app.app.test_client()
    aluno.post('/api/v1/auth/registrar', json={'nome_usuario': 'joao', 'email': 'joao@x.com', 'password': 'segredo1'})
    _bearer(aluno, 'joao@x.com', 'segredo1')
    r = aluno.post('/api/v1/teste-vocacional/resultados', json={'respostas': {p['id']: 'b' for p in PERGUNTAS}})
    assert r.status_code == 201 and r.get_json()['data']['salvo'] is True
    resultado_id = r.get_json()['data']['resultado_id']
    usuario_id = _sql("SELECT id FROM usuarios WHERE email='joao@x.com'")[0]['id']

    email_admin = _sql("SELECT email FROM usuarios WHERE tipo='admin'")[0]['email']
    admin = _bearer(app.app.test_client(), email_admin, 'admin123')
    r = admin.delete(f'/api/v1/admin/usuarios/{usuario_id}')
    assert r.status_code in (200, 204), r.get_data(as_text=True)
    assert _sql("SELECT usuario_id FROM teste_vocacional_resultados WHERE id=?", (resultado_id,)) == [{'usuario_id': None}]


def test_resultado_de_usuario_excluido_nao_e_acessivel_por_outra_conta(app, client):
    """usuario_id NULL também é o estado do teste anônimo: garantir que um
    resultado que ficou sem dono não vaze para outra pessoa."""
    usuario_id = _aluno_com_testes(client, n=1)
    resultado_id = _sql("SELECT id FROM teste_vocacional_resultados WHERE usuario_id=?", (usuario_id,))[0]['id']
    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    assert client.post('/api/usuario/deletar', data={'id': usuario_id}).get_json()['success'] is True
    client.post('/api/usuario/logout')

    outro = app.app.test_client()
    # Sem teste pendente na sessão: a prévia anônima não mostra o resultado órfão.
    assert outro.get('/api/teste_vocacional/resultado').status_code == 404
    outro.post('/api/v1/auth/registrar', json={'nome_usuario': 'eva', 'email': 'eva@x.com', 'password': 'segredo1'})
    _bearer(outro, 'eva@x.com', 'segredo1')
    assert outro.get(f'/api/v1/teste-vocacional/recomendacoes?id={resultado_id}').status_code == 404
    assert outro.get('/api/v1/teste-vocacional/resultados').get_json()['data'] == []
    # Login não "adota" o resultado órfão.
    assert _sql("SELECT usuario_id FROM teste_vocacional_resultados WHERE id=?", (resultado_id,)) == [{'usuario_id': None}]


def test_dashboard_e_historico_continuam_funcionando_apos_exclusao(app, client):
    _aluno_com_testes(client, n=1)
    vivo = _aluno_com_testes(client, username='ana', email='ana@x.com', n=1)
    morto = _sql("SELECT id FROM usuarios WHERE nome_usuario='maria'")[0]['id']
    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    client.post('/api/usuario/deletar', data={'id': morto})
    assert len(tvs.historico(vivo)) == 1
    client.post('/api/usuario/logout')
    client.post('/api/usuario/login', data={'username': 'ana', 'password': 'segredo123'})
    assert client.get('/dashboard').status_code == 200
    assert client.get('/api/teste_vocacional/recomendacoes').status_code == 200


# ── 3/4. Integridade das FKs e estrutura após init e migração ─────────────

def _fks_para_usuarios(conn):
    tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    fks = {}
    for t in tabelas:
        for fk in conn.execute(f"PRAGMA foreign_key_list({t})").fetchall():
            if fk[2] == 'usuarios':
                fks[t] = fk[6].upper()
    return fks


def test_banco_novo_tem_estrutura_e_fks_corretas(app):
    conn = get_connection()
    try:
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'vestibular_inscricoes' not in tabelas
        assert {'usuarios', 'faculdades', 'cursos', 'vestibulares', 'favoritos', 'teste_vocacional_resultados',
                'automacao_logs', 'refresh_tokens', 'cursos_catalogo'} <= tabelas
        # Toda FK para usuarios tem regra de exclusão explícita (nenhuma bloqueia o DELETE).
        assert _fks_para_usuarios(conn) == {'favoritos': 'CASCADE', 'refresh_tokens': 'CASCADE',
                                            'teste_vocacional_resultados': 'SET NULL'}
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        colunas = [r[1] for r in conn.execute("PRAGMA table_info(teste_vocacional_resultados)")]
        assert colunas == ['id', 'usuario_id', 'perfil_principal', 'perfis_json', 'respostas_json', 'created_at']
        indices = {r[1] for r in conn.execute("PRAGMA index_list(teste_vocacional_resultados)")}
        assert 'idx_teste_vocacional_usuario' in indices
    finally:
        conn.close()


ESQUEMA_ANTIGO = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_usuario TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'aluno' CHECK(tipo IN ('aluno','admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE vestibular_inscricoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    vestibular_id INTEGER NOT NULL,
    resultado TEXT NOT NULL DEFAULT 'pendente',
    observacao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, vestibular_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (vestibular_id) REFERENCES vestibulares(id) ON DELETE CASCADE
);
CREATE TABLE teste_vocacional_resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NULL,
    perfil_principal TEXT NOT NULL,
    perfis_json TEXT NOT NULL,
    respostas_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
"""


def _criar_banco_antigo(caminho, inscricoes=0):
    conn = sqlite3.connect(caminho)
    conn.executescript(ESQUEMA_ANTIGO)
    conn.execute("INSERT INTO usuarios (id, nome_usuario, email, senha) VALUES (1,'ana','ana@x.com','x'), "
                 "(2,'bia','bia@x.com','x')")
    linhas = [(1, 1, 'tecnico', '2025-01-01 10:00:00'), (2, None, 'humano', '2025-01-02 10:00:00'),
              (3, 99, 'gestao', '2025-01-03 10:00:00'),  # órfão (gravado com foreign_keys desligado)
              (4, 2, 'criativo', '2025-01-04 10:00:00'), (5, 2, 'pratico', '2025-01-05 10:00:00')]
    for i, u, perfil, data in linhas:
        conn.execute("INSERT INTO teste_vocacional_resultados (id, usuario_id, perfil_principal, perfis_json, "
                     "respostas_json, created_at) VALUES (?,?,?,?,?,?)",
                     (i, u, perfil, json.dumps({'scores': {perfil: 5}}), '{"q1": "a"}', data))
    conn.execute("DELETE FROM teste_vocacional_resultados WHERE id IN (4, 5)")  # sqlite_sequence fica em 5
    for i in range(inscricoes):
        conn.execute("INSERT INTO vestibular_inscricoes (usuario_id, vestibular_id) VALUES (1, ?)", (i + 1,))
    conn.commit()
    conn.close()


@pytest.fixture()
def app_banco_antigo(tmp_path, monkeypatch):
    from tests.conftest import build_app
    caminho = tmp_path / 'antigo.db'
    _criar_banco_antigo(str(caminho))
    monkeypatch.setenv('SUAFACUL_DB_PATH', str(caminho))
    return build_app(monkeypatch)


def test_migracao_de_banco_existente_aplica_set_null_e_preserva_dados(app_banco_antigo):
    conn = get_connection()
    try:
        assert _fks_para_usuarios(conn)['teste_vocacional_resultados'] == 'SET NULL'
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'vestibular_inscricoes' not in tabelas  # vazia → removida
        assert 'teste_vocacional_resultados_nova' not in tabelas
        linhas = [dict(r) for r in conn.execute(
            "SELECT id, usuario_id, perfil_principal, respostas_json, created_at "
            "FROM teste_vocacional_resultados ORDER BY id")]
    finally:
        conn.close()
    assert linhas == [
        {'id': 1, 'usuario_id': 1, 'perfil_principal': 'tecnico', 'respostas_json': '{"q1": "a"}',
         'created_at': '2025-01-01 10:00:00'},
        {'id': 2, 'usuario_id': None, 'perfil_principal': 'humano', 'respostas_json': '{"q1": "a"}',
         'created_at': '2025-01-02 10:00:00'},
        {'id': 3, 'usuario_id': None, 'perfil_principal': 'gestao', 'respostas_json': '{"q1": "a"}',
         'created_at': '2025-01-03 10:00:00'},  # vínculo órfão anulado
    ]
    # AUTOINCREMENT preservado: ids 4 e 5 (já usados e apagados) não são reutilizados.
    novo = tvs.submeter({p['id']: 'a' for p in PERGUNTAS}, usuario_id=None)
    assert novo['resultado_id'] == 6
    # Depois da migração a exclusão funciona e preserva o resultado.
    _escrever("DELETE FROM usuarios WHERE id=1")
    assert _sql("SELECT usuario_id FROM teste_vocacional_resultados WHERE id=1") == [{'usuario_id': None}]


def test_migracao_e_idempotente(app_banco_antigo):
    from database.init_db import _migrar_fk_teste_vocacional, init_db
    antes = _sql("SELECT * FROM teste_vocacional_resultados ORDER BY id")
    init_db()
    init_db()
    conn = get_connection()
    try:
        assert _migrar_fk_teste_vocacional(conn) is False
    finally:
        conn.close()
    assert _sql("SELECT * FROM teste_vocacional_resultados ORDER BY id") == antes


def test_vestibular_inscricoes_com_dados_nao_e_apagada(tmp_path, monkeypatch, capsys):
    from tests.conftest import build_app
    caminho = tmp_path / 'com_inscricoes.db'
    _criar_banco_antigo(str(caminho), inscricoes=2)
    monkeypatch.setenv('SUAFACUL_DB_PATH', str(caminho))
    build_app(monkeypatch)
    assert _sql("SELECT COUNT(*) AS n FROM vestibular_inscricoes")[0]['n'] == 2
    assert 'vestibular_inscricoes (tabela obsoleta) tem 2 linha(s)' in capsys.readouterr().out


# ── 5/6. Estatísticas: faculdades importadas do e-MEC ─────────────────────

def _faculdade(nome, fonte, codigo=None):
    _escrever("INSERT INTO faculdades (nome, codigo_emec, fonte, tipo_instituicao) VALUES (?,?,?, 'Privada')",
              (nome, codigo, fonte))


def test_estatistica_conta_emec_e_emec_csv_upload_sem_duplicar(app, admin_client):
    from app.models.estatisticas import Estatisticas
    from app.models.faculdade import FONTES_EMEC
    assert set(FONTES_EMEC) == {'emec', 'emec_csv_upload'}
    base = Estatisticas().resumo_admin()
    _faculdade('IES Scraping A', 'emec', '9001')
    _faculdade('IES Scraping B', 'emec', '9002')
    _faculdade('IES Upload C', 'emec_csv_upload', '9003')
    _faculdade('IES Manual D', 'manual')
    _faculdade('IES Sem Fonte E', None)

    stats = admin_client.get('/api/admin/stats').get_json()['stats']
    assert stats['faculdades_importadas_emec'] == base['faculdades_importadas_emec'] + 3
    assert stats['total_faculdades'] == base['total_faculdades'] + 5
    # Confere com os registros reais do banco (uma linha = uma faculdade).
    reais = _sql("SELECT COUNT(DISTINCT id) AS n FROM faculdades WHERE fonte IN ('emec','emec_csv_upload')")[0]['n']
    assert stats['faculdades_importadas_emec'] == reais
    assert stats['faculdades_importadas_emec'] <= stats['total_faculdades']


def test_reimportacao_nao_duplica_a_contagem(app):
    """O mesmo código e-MEC importado pelas duas vias vira UMA faculdade."""
    from app.models.estatisticas import Estatisticas
    from app.models.faculdade import Faculdade
    base = Estatisticas().resumo_admin()['faculdades_importadas_emec']
    dados = {'codigo_emec': '7777', 'nome': 'FACULDADE TESTE DUPLA', 'sigla': None,
             'organizacao_academica': 'Faculdade', 'tipo_instituicao': 'Privada', 'url': '', 'endereco': '',
             'cidade': '', 'uf': 'SP', 'telefone': '', 'email': '', 'situacao': 'ativa', 'fonte': 'emec'}
    Faculdade().upsert_por_codigo_emec(dados)
    Faculdade().upsert_por_codigo_emec({**dados, 'fonte': 'emec_csv_upload'})
    Faculdade().upsert_por_codigo_emec({**dados, 'fonte': 'emec_csv_upload'})
    assert Estatisticas().resumo_admin()['faculdades_importadas_emec'] == base + 1


def test_upload_csv_conta_nas_estatisticas(app, admin_client):
    """Fluxo real: upload do CSV oficial grava fonte='emec_csv_upload' e o painel conta."""
    from app.services import emec_service
    from app.models.estatisticas import Estatisticas
    base = Estatisticas().resumo_admin()['faculdades_importadas_emec']
    instituicoes = [{'codigo_emec': str(8000 + i), 'nome': f'INSTITUICAO CSV {i}', 'sigla': None,
                     'organizacao_academica': 'Faculdade', 'tipo_instituicao': 'Privada', 'cidade': 'X',
                     'uf': 'SP', 'situacao': 'ativa'} for i in range(3)]
    original = emec_service._parsear_csv_dados_abertos
    emec_service._parsear_csv_dados_abertos = lambda _b: instituicoes
    try:
        r = emec_service.importar_instituicoes_de_csv_upload(b'ignorado')
    finally:
        emec_service._parsear_csv_dados_abertos = original
    assert r['criadas'] == 3
    assert Estatisticas().resumo_admin()['faculdades_importadas_emec'] == base + 3
    assert admin_client.get('/api/admin/stats').get_json()['stats']['faculdades_importadas_emec'] == base + 3


# ── 7/8. Pontuação única: Web (/salvar), /responder e API v1 ───────────────

def _id_para_valor(respostas_id):
    return {p['id']: tvs.valor_da_opcao(next(o for o in p['opcoes'] if o['id'] == respostas_id[p['id']]))
            for p in PERGUNTAS}


def test_formatos_id_e_valor_dao_a_mesma_pontuacao_em_todas_as_combinacoes():
    """Exaustivo: todas as combinações de respostas possíveis do questionário."""
    opcoes = [[o['id'] for o in p['opcoes']] for p in PERGUNTAS]
    total = 0
    for combinacao in itertools.product(*opcoes):
        respostas = dict(zip((p['id'] for p in PERGUNTAS), combinacao))
        assert tvs.calcular(respostas) == tvs.calcular(_id_para_valor(respostas), formato='valor')
        total += 1
    assert total == 384000


def test_pontuacao_e_identica_em_todos_os_endpoints(app):
    rnd = random.Random(2026)
    web = app.app.test_client()
    legado = app.app.test_client()
    api = app.app.test_client()
    for _ in range(15):
        respostas = {p['id']: rnd.choice(p['opcoes'])['id'] for p in PERGUNTAS}
        esperado = tvs.calcular(respostas)

        r = web.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(_id_para_valor(respostas))})
        assert r.status_code == 200, r.get_json()
        salvo = _sql("SELECT perfil_principal, perfis_json FROM teste_vocacional_resultados WHERE id=?",
                     (r.get_json()['id'],))[0]
        web_json = json.loads(salvo['perfis_json'])

        r = legado.post('/api/teste_vocacional/responder', data=respostas)
        assert r.status_code == 200
        responder = r.get_json()

        r = api.post('/api/v1/teste-vocacional/resultados', json={'respostas': respostas})
        assert r.status_code == 201
        v1 = r.get_json()['data']

        assert web_json['scores'] == responder['scores'] == v1['scores'] == esperado['scores']
        assert web_json['bestProfiles'] == [p['chave'] for p in responder['perfis']] \
            == [p['chave'] for p in v1['perfis']] == esperado['perfis_principais']
        assert salvo['perfil_principal'] == esperado['perfis_principais'][0]
        assert responder['pontuacoes'] == v1['pontuacoes']
        # A prévia web mostra a mesma distribuição percentual.
        previa = web.get('/api/teste_vocacional/resultado').get_json()['resultado']
        assert previa['pontuacoes'] == v1['pontuacoes']


def test_validacao_equivalente_e_mensagens_do_salvar_preservadas(client, app):
    validas = {p['id']: 'a' for p in PERGUNTAS}
    valores = _id_para_valor(validas)

    sem_q3 = {k: v for k, v in valores.items() if k != 'q3'}
    r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(sem_q3)})
    assert r.status_code == 400 and r.get_json()['message'] == 'Responda todas as perguntas do teste.'

    forjada = {**valores, 'q2': 'tecnico,tecnico'}
    r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(forjada)})
    assert r.status_code == 400 and r.get_json()['message'] == 'Resposta inválida na pergunta 2.'

    for corpo in ('{nao e json', '["lista"]'):
        r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': corpo})
        assert r.status_code == 400 and r.get_json()['message'] == 'Respostas em formato inválido.'

    # API v1 e /responder rejeitam o mesmo problema (mesma validação).
    r = app.app.test_client().post('/api/v1/teste-vocacional/resultados',
                                   json={'respostas': {**validas, 'q2': 'z'}})
    assert r.status_code == 422
    assert r.get_json()['error']['details']['respostas_invalidas'] == ['q2']
    r = app.app.test_client().post('/api/teste_vocacional/responder', data={**validas, 'q2': 'z'})
    # Contrato legado (app/errors.py): erro de negócio fora da v1 = 200 + success False.
    assert r.status_code == 200 and r.get_json()['success'] is False


def test_existe_uma_unica_implementacao_da_pontuacao():
    from app.services import vocacional_service
    assert not hasattr(vocacional_service, 'calcular_pontuacao')
    assert not hasattr(vocacional_service, 'validar_respostas')
    import inspect
    from app.routes import api_teste_vocacional
    fonte = inspect.getsource(api_teste_vocacional)
    assert 'teste_vocacional_service.calcular(' in fonte
    assert 'scores[' not in fonte  # nenhuma soma de pontos na rota
