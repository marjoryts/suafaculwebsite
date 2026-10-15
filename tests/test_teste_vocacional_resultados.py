"""Resultados do Teste Vocacional: pontuação no servidor, compatibilidade
com os cursos do banco, bloqueio da lista completa para quem não está
logado e recuperação do resultado após login/cadastro."""
import json

from app.services import vocacional_service as vs

# Respostas predominantemente "técnico" (alternativas reais do template)
RESPOSTAS_TECNICO = {
    'q1': 'tecnico,cientifico', 'q2': 'tecnico,pratico', 'q3': 'tecnico,cientifico',
    'q4': 'tecnico', 'q5': 'tecnico,pratico', 'q6': 'tecnico,cientifico,humano',
    'q7': 'tecnico,cientifico', 'q8': 'cientifico,tecnico', 'q9': 'criativo,tecnico,pratico',
    'q10': 'tecnico',
}
RESPOSTAS_HUMANO = {
    'q1': 'humano', 'q2': 'humano', 'q3': 'humano', 'q4': 'humano',
    'q5': 'humano,gestao,criativo', 'q6': 'tecnico,cientifico,humano', 'q7': 'humano',
    'q8': 'pratico,gestao', 'q9': 'humano,cientifico', 'q10': 'humano',
}


def _concluir_teste(client, respostas=RESPOSTAS_TECNICO):
    r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(respostas)})
    assert r.status_code == 200, r.get_json()
    return r.get_json()


def _registrar(client, username='joana', email='joana@exemplo.com', senha='segredo123'):
    r = client.post('/api/usuario/registrar', data={'username': username, 'email': email, 'password': senha})
    assert r.get_json()['success'] is True


def _logar(client, username='joana', senha='segredo123'):
    r = client.post('/api/usuario/login', data={'username': username, 'password': senha})
    assert r.get_json()['success'] is True
    return r.get_json()['user']


def _limpar_cursos():
    from config.database import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM cursos")
    conn.commit()
    conn.close()


# ── Regra de cálculo ──

def test_pontuacao_no_servidor_igual_a_do_front():
    scores, melhores = vs.calcular_pontuacao(RESPOSTAS_TECNICO)
    assert scores['tecnico'] == 10
    assert melhores == ['tecnico']


def test_respostas_invalidas_ou_incompletas_sao_rejeitadas(client):
    incompletas = dict(RESPOSTAS_TECNICO)
    incompletas.pop('q10')
    r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(incompletas)})
    assert r.status_code == 400
    forjadas = dict(RESPOSTAS_TECNICO, q4='tecnico,tecnico,tecnico')
    r = client.post('/api/teste_vocacional/salvar', data={'respostas_json': json.dumps(forjadas)})
    assert r.status_code == 400


def test_scores_enviados_pelo_cliente_sao_ignorados(app, client):
    _concluir_teste(client)
    client.post('/api/teste_vocacional/salvar', data={
        'respostas_json': json.dumps(RESPOSTAS_HUMANO),
        'perfil_principal': 'tecnico',
        'perfis_json': json.dumps({'scores': {'tecnico': 999}}),
    })
    previa = client.get('/api/teste_vocacional/resultado').get_json()
    assert previa['resultado']['perfil'] == 'humano'


def test_compatibilidade_usa_nome_depois_area_e_ignora_sem_dados():
    assert vs.perfis_do_curso('Psicologia', 'Saúde') == (['humano'], 'nome')
    assert vs.perfis_do_curso('Nutrição', 'Saúde') == (['humano', 'cientifico'], 'area')
    assert vs.perfis_do_curso('Educação Física', 'Saúde e bem-estar') == (['humano', 'cientifico'], 'area')
    assert vs.perfis_do_curso('Curso Misterioso', None) == ([], None)
    afin = vs.afinidades({'tecnico': 10})
    assert vs.compatibilidade(['tecnico'], afin) == 100
    assert vs.compatibilidade(['tecnico', 'pratico'], afin) == 50
    assert vs.compatibilidade([], afin) is None


# ── Cenário 1 e 2: deslogado ──

def test_deslogado_conclui_teste_e_ve_apenas_a_previa(client):
    salvo = _concluir_teste(client)
    assert salvo['autenticado'] is False
    assert salvo['redirect'] == '/testevocacional/resultado'

    previa = client.get('/api/teste_vocacional/resultado').get_json()
    assert previa['success'] is True
    assert previa['autenticado'] is False
    assert previa['resultado']['perfil_nome'] == 'Perfil Técnico / Exato'
    assert previa['total_compativeis'] > 0
    assert 'cursos' not in previa                     # nenhuma lista na prévia

    html = client.get('/testevocacional/resultado').data.decode()
    assert 'Seus resultados vocacionais' in html
    assert 'Engenharia de Software' not in html       # nada de curso no HTML


def test_deslogado_nao_acessa_resultados_completos(client):
    _concluir_teste(client)
    r = client.get('/api/teste_vocacional/recomendacoes')
    assert r.status_code == 401
    assert r.get_json()['motivo'] == 'nao_autenticado'
    assert 'cursos' not in r.get_json()


def test_deslogado_sem_teste_recebe_404_na_previa(client):
    r = client.get('/api/teste_vocacional/resultado')
    assert r.status_code == 404
    assert r.get_json()['motivo'] == 'sem_resultado'


# ── Cenário 3 e 4: login / cadastro depois do teste ──

def test_login_apos_teste_recupera_os_resultados(client):
    _registrar(client)
    _concluir_teste(client)                           # ainda deslogado
    user = _logar(client)
    rec = client.get('/api/teste_vocacional/recomendacoes').get_json()
    assert rec['success'] is True
    assert rec['perfil'] == 'tecnico'
    assert len(rec['cursos']) > 0
    # o resultado agora pertence à conta e aparece no dashboard
    html = client.get('/dashboard').data.decode()
    assert 'Perfil Técnico / Exato' in html
    assert user['id']


def test_novo_usuario_conclui_teste_cria_conta_e_ve_recomendacoes(client):
    _concluir_teste(client, RESPOSTAS_HUMANO)
    _registrar(client, 'novato', 'novato@exemplo.com')
    _logar(client, 'novato')                          # o login.html entra logo após o cadastro
    rec = client.get('/api/teste_vocacional/recomendacoes').get_json()
    assert rec['success'] is True
    assert rec['perfil'] == 'humano'
    assert rec['cursos'][0]['nome'] == 'Psicologia'


def test_resultado_nao_vai_para_outra_conta(app, client):
    _registrar(client, 'ana', 'ana@exemplo.com')
    _registrar(client, 'bruno', 'bruno@exemplo.com')
    _logar(client, 'ana')
    _concluir_teste(client)                           # resultado da Ana
    id_ana = client.get('/api/teste_vocacional/resultado').get_json()['resultado']['id']
    client.get('/logout')
    _logar(client, 'bruno')
    # Bruno não tem teste e não pode pedir o da Ana pelo id
    assert client.get('/api/teste_vocacional/recomendacoes').status_code == 404
    assert client.get(f'/api/teste_vocacional/recomendacoes?id={id_ana}').status_code == 404
    # e vincular um resultado que já tem dono não faz nada
    assert app.TesteVocacional().vincular_a_usuario(id_ana, 999) is False


def test_logout_descarta_vinculo_pendente(client):
    _registrar(client, 'carla', 'carla@exemplo.com')
    _concluir_teste(client)
    client.get('/logout')                             # sessão limpa
    _logar(client, 'carla')
    assert client.get('/api/teste_vocacional/recomendacoes').status_code == 404


# ── Cenário 5, 6 e 7: autenticado, ordem e recarregar ──

def test_autenticado_conclui_teste_e_acessa_normalmente(client):
    _registrar(client)
    _logar(client)
    salvo = _concluir_teste(client)
    assert salvo['autenticado'] is True
    previa = client.get('/api/teste_vocacional/resultado').get_json()
    assert previa['autenticado'] is True
    rec = client.get(f"/api/teste_vocacional/recomendacoes?id={previa['resultado']['id']}").get_json()
    assert rec['success'] is True and rec['resultado_id'] == previa['resultado']['id']


def test_recomendacoes_em_ordem_decrescente(client):
    _registrar(client)
    _logar(client)
    _concluir_teste(client)
    cursos = client.get('/api/teste_vocacional/recomendacoes').get_json()['cursos']
    pcts = [c['compatibilidade'] for c in cursos]
    assert pcts == sorted(pcts, reverse=True)
    assert all(0 < p <= 100 for p in pcts)
    assert cursos[0]['compatibilidade'] == 100       # cursos de tecnologia no topo
    assert 'Administração' not in [c['nome'] for c in cursos]   # 0% não é recomendado


def test_resultado_continua_disponivel_apos_recarregar(client):
    _concluir_teste(client)
    primeira = client.get('/api/teste_vocacional/resultado').get_json()
    segunda = client.get('/api/teste_vocacional/resultado').get_json()
    assert primeira['resultado']['id'] == segunda['resultado']['id']
    assert client.get('/testevocacional/resultado').status_code == 200


# ── Cenário 8: erros, ausência de cursos, sessão expirada ──

def test_sem_cursos_cadastrados_retorna_lista_vazia(app, client):
    _limpar_cursos()
    _registrar(client)
    _logar(client)
    _concluir_teste(client)
    rec = client.get('/api/teste_vocacional/recomendacoes').get_json()
    assert rec['success'] is True
    assert rec['cursos'] == [] and rec['total_compativeis'] == 0


def test_sessao_expirada_volta_a_pedir_login(client):
    _registrar(client)
    _logar(client)
    _concluir_teste(client)
    with client.session_transaction() as s:
        s.clear()                                     # simula cookie de sessão expirado
    assert client.get('/api/teste_vocacional/recomendacoes').status_code == 401


def test_erro_no_calculo_retorna_500_tratado(app, client, monkeypatch):
    _registrar(client)
    _logar(client)
    _concluir_teste(client)

    def falha(*a, **k):
        raise RuntimeError('banco indisponível')
    monkeypatch.setattr(app.vocacional_service, 'recomendar_cursos', falha)
    r = client.get('/api/teste_vocacional/recomendacoes')
    assert r.status_code == 500
    assert r.get_json()['motivo'] == 'erro_interno'


def test_redirect_do_google_so_aceita_caminho_interno(app):
    assert app._destino_seguro('/testevocacional/resultado') == '/testevocacional/resultado'
    assert app._destino_seguro('//site-malicioso.com') is None
    assert app._destino_seguro('https://site-malicioso.com') is None


def test_cliente_legado_sem_respostas_continua_funcionando(client):
    r = client.post('/api/teste_vocacional/salvar', data={
        'perfil_principal': 'criativo',
        'perfis_json': json.dumps({'scores': {'criativo': 6, 'tecnico': 2}}),
    })
    assert r.get_json()['success'] is True
