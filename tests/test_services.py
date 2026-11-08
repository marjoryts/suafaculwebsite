"""Etapa 3: regras de negócio nos services (compartilhados por Web, API, CLI)."""
import json

import pytest

from app.services import (dashboard_service, favorito_service, teste_vocacional_service as tv,
                          usuario_service)
from app.services.erros import ErroDeNegocio, NaoEncontradoError, PermissaoNegadaError, ValidacaoError
from app.services.paginacao import inteiro, paginar
from config.database import get_connection

TODAS_A = {f'q{i}': 'a' for i in range(1, 11)}


def _criar_usuario(app, nome='ana', email='ana@x.com', senha='segredo1'):
    app.Usuario().criar(nome, email, senha)
    return app.Usuario().buscar_por_email(email)['id']


# ── Teste vocacional ────────────────────────────────────────────────────

def test_questionario_tem_10_perguntas_e_nao_vaza_os_pesos():
    q = tv.questionario()
    perguntas = [p for s in q['secoes'] for p in s['perguntas']]
    assert [p['id'] for p in perguntas] == [f'q{i}' for i in range(1, 11)]
    assert sum(len(p['opcoes']) for p in perguntas) == 39
    assert all(set(o) == {'id', 'texto'} for p in perguntas for o in p['opcoes'])  # sem 'perfis'


def test_pontuacao_calculada_no_servidor():
    # Conta manual para "tudo a": tecnico em q1,q3,q5,q8,q9,q10 = 6
    r = tv.calcular(TODAS_A)
    assert r['scores'] == {'tecnico': 6, 'criativo': 1, 'humano': 2, 'gestao': 3,
                           'cientifico': 3, 'pratico': 2}
    assert r['perfis_principais'] == ['tecnico']


def test_empate_devolve_todos_os_perfis_na_ordem_padrao(monkeypatch):
    def q(id, perfil):
        return {'id': id, 'texto': id, 'opcoes': [{'id': 'a', 'texto': 'x', 'perfis': [perfil]}]}
    monkeypatch.setattr(tv, 'SECOES', [{'titulo': 'T', 'perguntas': [q('q1', 'humano'), q('q2', 'tecnico')]}])
    assert tv.calcular({'q1': 'a', 'q2': 'a'})['perfis_principais'] == ['tecnico', 'humano']


def test_calcular_exige_todas_as_perguntas():
    with pytest.raises(ValidacaoError) as e:
        tv.calcular({'q1': 'a'})
    assert 'q2' in e.value.details['perguntas_sem_resposta']


def test_calcular_rejeita_opcao_inexistente():
    respostas = {**TODAS_A, 'q1': 'zzz'}
    with pytest.raises(ValidacaoError) as e:
        tv.calcular(respostas)
    assert e.value.details['respostas_invalidas'] == ['q1']


def test_submeter_anonimo_salva_sem_usuario_e_sugere_cursos(app):
    app.Curso().criar({'nome': 'Ciência da Computação X', 'instituicao': 'Inst', 'faculdade_id': None,
                       'modalidade': 'presencial', 'descricao': '', 'duracao': '', 'grau': '',
                       'area': 'Tecnologia', 'tipo_instituicao': 'Pública'})
    r = tv.submeter(TODAS_A, usuario_id=None)
    assert r['salvo'] is True
    assert [p['chave'] for p in r['perfis']] == ['tecnico']
    assert any(c['nome'] == 'Ciência da Computação X' for c in r['perfis'][0]['cursos_sugeridos'])
    conn = get_connection()
    linha = conn.execute("SELECT usuario_id, perfil_principal, perfis_json FROM teste_vocacional_resultados").fetchone()
    conn.close()
    assert linha['usuario_id'] is None and linha['perfil_principal'] == 'tecnico'
    assert json.loads(linha['perfis_json'])['scores']['tecnico'] == 6


def test_historico_do_usuario_traz_percentuais(app):
    uid = _criar_usuario(app)
    tv.submeter(TODAS_A, usuario_id=uid)
    h = tv.historico(uid)
    assert len(h) == 1 and h[0]['perfil_nome'] == 'Perfil Técnico / Exato'
    assert h[0]['pontuacoes'][0] == {'chave': 'tecnico', 'nome': 'Perfil Técnico / Exato', 'percentual': 35}  # 6 de 17 pontos


def test_rota_responder_pontua_no_servidor_e_ignora_pontuacao_do_cliente(client):
    data = {**TODAS_A, 'perfil_principal': 'humano', 'scores': '{"humano": 99}'}  # tentativa de forjar
    r = client.post('/api/teste_vocacional/responder', data=data).get_json()
    assert r['success'] is True and [p['chave'] for p in r['perfis']] == ['tecnico']


def test_rota_responder_com_respostas_incompletas_devolve_mensagem(client):
    r = client.post('/api/teste_vocacional/responder', data={'q1': 'a'})
    assert r.status_code == 200 and r.get_json()['success'] is False
    assert 'Responda todas' in r.get_json()['message']


def test_rota_perguntas_e_pagina_renderizam_o_mesmo_questionario(client):
    """A página (formato da Web: value = perfis da opção) e a API do app vêm da
    mesma fonte (teste_vocacional_dados): mesmos textos, mesmas opções."""
    from app.services.teste_vocacional_dados import SECOES
    api = client.get('/api/teste_vocacional/perguntas').get_json()
    html = client.get('/testevocacional').data.decode()
    opcoes_fonte = {p['id']: p['opcoes'] for s in SECOES for p in s['perguntas']}
    for secao in api['secoes']:
        for pergunta in secao['perguntas']:
            assert pergunta['texto'] in html
            for opcao, fonte in zip(pergunta['opcoes'], opcoes_fonte[pergunta['id']]):
                assert opcao['texto'] in html
                assert f'name="{pergunta["id"]}" value="{",".join(fonte["perfis"])}"' in html
    assert html.count('type="radio"') == 39


def test_salvar_legado_rejeita_perfil_e_pontuacao_invalidos(client):
    ruim = client.post('/api/teste_vocacional/salvar', data={'perfil_principal': 'hacker'}).get_json()
    assert ruim['success'] is False
    ruim2 = client.post('/api/teste_vocacional/salvar', data={
        'perfil_principal': 'humano', 'perfis_json': json.dumps({'scores': {'humano': 'muito'}})}).get_json()
    assert ruim2['success'] is False


# ── Usuário ─────────────────────────────────────────────────────────────

def test_registrar_valida_campos_email_e_senha(app):
    with app.app.app_context():  # o código de verificação usa a chave secreta da aplicação
        _registrar_valida_campos()


def _registrar_valida_campos():
    with pytest.raises(ValidacaoError):
        usuario_service.registrar('', 'a@b.com', 'segredo1')
    with pytest.raises(ValidacaoError, match='e-mail'):
        usuario_service.registrar('bob', 'sem-arroba', 'segredo1')
    with pytest.raises(ValidacaoError, match='8 caracteres'):
        usuario_service.registrar('bob', 'bob@b.com', '123')
    with pytest.raises(ValidacaoError, match='letras e números'):
        usuario_service.registrar('bob', 'bob@b.com', 'somenteletras')
    assert usuario_service.registrar('bob', 'bob@b.com', 'segredo1')['success'] is True


def test_definir_tipo_protege_o_proprio_acesso_de_admin(app):
    admin_id = app.Usuario().buscar_por_email('admin@suafacul.local')['id']
    with pytest.raises(PermissaoNegadaError):
        usuario_service.definir_tipo(admin_id, admin_id, 'aluno')
    outro = _criar_usuario(app)
    assert usuario_service.definir_tipo(admin_id, outro, 'admin')['success'] is True


def test_excluir_protege_a_propria_conta_e_valida_id(app):
    admin_id = app.Usuario().buscar_por_email('admin@suafacul.local')['id']
    with pytest.raises(PermissaoNegadaError):
        usuario_service.excluir(admin_id, admin_id)
    with pytest.raises(ValidacaoError):
        usuario_service.excluir(admin_id, 'abc')


def test_atualizar_perfil_detecta_conflito_sem_depender_do_texto_do_sqlite(app):
    a = _criar_usuario(app, 'ana', 'ana@x.com')
    _criar_usuario(app, 'bia', 'bia@x.com')
    with pytest.raises(ValidacaoError, match='já está em uso'):
        usuario_service.atualizar_perfil(a, 'bia', 'ana@x.com')
    assert usuario_service.atualizar_perfil(a, 'ana', 'ana@x.com', 'novasenha1', 'novasenha1',
                                            senha_atual='segredo1')['success'] is True
    with pytest.raises(ValidacaoError, match='confirmação'):
        usuario_service.atualizar_perfil(a, 'ana', 'ana@x.com', 'novasenha2', 'outra', senha_atual='novasenha1')
    with pytest.raises(ValidacaoError, match='Senha atual incorreta'):
        usuario_service.atualizar_perfil(a, 'ana', 'ana@x.com', 'novasenha2', 'novasenha2', senha_atual='errada')


def test_erro_de_negocio_vira_resposta_legada_sem_500(admin_client):
    r = admin_client.post('/api/usuario/deletar', data={'id': 'abc'})
    assert r.status_code == 200 and r.get_json() == {'success': False, 'message': 'ID inválido.'}


# ── Favoritos ───────────────────────────────────────────────────────────

def test_favoritos_validam_entrada_sem_gerar_500(client):
    client.post('/api/usuario/registrar', data={'username': 'fav', 'email': 'fav@x.com', 'password': 'segredo1'})
    client.post('/api/usuario/login', data={'username': 'fav', 'password': 'segredo1'})
    assert client.post('/api/favoritos/adicionar', data={'tipo': 'curso', 'item_id': 'abc', 'nome_item': 'X'}).status_code == 200
    r = client.post('/api/favoritos/adicionar', data={'tipo': 'curso', 'item_id': 'abc', 'nome_item': 'X'}).get_json()
    assert r == {'success': False, 'message': 'Dados incompletos.'}
    r = client.post('/api/favoritos/adicionar', data={'tipo': 'foo', 'item_id': 1, 'nome_item': 'X'}).get_json()
    assert r['message'] == 'Tipo inválido.'
    assert client.get('/api/favoritos/listar-ids?tipo=foo').get_json()['message'] == 'Tipo inválido.'


def test_favorito_service_ciclo_completo(app):
    uid = _criar_usuario(app)
    assert favorito_service.adicionar(uid, 'curso', 7, 'Curso 7')['success'] is True
    assert favorito_service.verificar(uid, 'curso', 7) is True
    assert favorito_service.listar_ids(uid, 'curso') == [7]
    assert favorito_service.remover(uid, 'curso', 7)['success'] is True
    with pytest.raises(ValidacaoError):
        favorito_service.remover(uid, 'curso', 0)


# ── Paginação ───────────────────────────────────────────────────────────

def test_inteiro_nunca_levanta():
    assert inteiro('abc', 1) == 1 and inteiro(None, 10) == 10 and inteiro('-5', 1) == 1 and inteiro('3', 1) == 3


def test_paginar_calcula_total_e_paginas(app):
    for i in range(5):
        app.Curso().criar({'nome': f'Zzpag {i}', 'instituicao': 'Inst', 'faculdade_id': None,
                           'modalidade': 'presencial', 'descricao': '', 'duracao': '', 'grau': '',
                           'area': '', 'tipo_instituicao': 'Pública'})
    r = paginar(app.Curso(), {'busca': 'Zzpag'}, page=2, limit=2, chave='cursos')
    assert r['total'] == 5 and r['total_pages'] == 3 and r['page'] == 2 and len(r['cursos']) == 2


def test_listagens_toleram_page_e_limit_invalidos(client):
    for rota in ('/api/cursos/listar', '/api/faculdades/listar', '/api/vestibulares/listar'):
        r = client.get(f'{rota}?page=abc&limit=xyz&mes=foo')
        assert r.status_code == 200 and r.get_json()['success'] is True and r.get_json()['page'] == 1


# ── Dashboard ───────────────────────────────────────────────────────────

def test_dashboard_service_resume_e_falha_para_usuario_inexistente(app):
    uid = _criar_usuario(app)
    tv.submeter(TODAS_A, usuario_id=uid)
    r = dashboard_service.resumo(uid)
    assert r['usuario']['id'] == uid and r['stats_favoritos'] == {'cursos': 0, 'faculdades': 0, 'vestibulares': 0}
    assert r['ultimo_teste']['perfil'] == 'tecnico'
    with pytest.raises(NaoEncontradoError):
        dashboard_service.resumo(999999)


def test_todos_os_erros_de_negocio_herdam_da_mesma_base():
    assert issubclass(ValidacaoError, ErroDeNegocio) and ValidacaoError.status == 422
    assert PermissaoNegadaError.status == 403 and NaoEncontradoError.status == 404


# ── CLI (CLI → services → banco) ────────────────────────────────────────

def test_cli_validar_vestibulares_registra_execucao(app):
    from app.models.automacao_log import AutomacaoLog
    r = app.app.test_cli_runner().invoke(args=['validar-vestibulares', '--aplicar'])
    assert r.exit_code == 0, r.output
    assert '"aplicado": true' in r.output
    assert AutomacaoLog().ultimos(1)[0]['tipo'] == 'validacao_vestibulares_cli'


def test_cli_importar_cursos_arquivo_invalido_falha_e_registra(app, tmp_path):
    from app.models.automacao_log import AutomacaoLog
    ruim = tmp_path / 'errado.csv'
    ruim.write_text('a;b\n1;2\n', encoding='latin-1')
    r = app.app.test_cli_runner().invoke(args=['importar-cursos', str(ruim)])
    assert r.exit_code != 0 and 'Colunas esperadas' in r.output
    ultimo = AutomacaoLog().ultimos(1)[0]
    assert ultimo['tipo'] == 'importacao_cursos_censo' and ultimo['sucesso'] is False
