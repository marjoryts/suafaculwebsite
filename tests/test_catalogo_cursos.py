"""Catálogo ampliado de cursos/instituições (database/catalogo_dados.py) e a
grade de cursos com imagens da página inicial."""
import os
import sqlite3

from database.catalogo_dados import CURSOS, INSTITUICOES

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _db():
    return sqlite3.connect(os.environ['SUAFACUL_DB_PATH'])


# ── Dados ──

def test_dados_do_catalogo_sao_consistentes():
    nomes = [c['nome'].lower() for c in CURSOS]
    assert len(nomes) == len(set(nomes)), 'curso duplicado no catálogo'
    imagens = [c['imagem'] for c in CURSOS]
    assert len(imagens) == len(set(imagens)), 'cada curso deve ter uma imagem própria'
    assert all(i.startswith('https://images.unsplash.com/photo-') for i in imagens)
    assert len({c['area'] for c in CURSOS}) >= 8, 'catálogo deve cobrir várias áreas'
    for curso in CURSOS:
        siglas = [o[0] for o in curso['ofertas']]
        assert len(siglas) == len(set(siglas)), f"oferta repetida em {curso['nome']}"
        for oferta in curso['ofertas']:
            assert oferta[0] in INSTITUICOES, f'instituição desconhecida: {oferta[0]}'
            assert oferta[1] in ('presencial', 'ead', 'semipresencial')
    for sigla, (nome, _org, tipo, url, _end, cidade, uf) in INSTITUICOES.items():
        assert tipo in ('Pública', 'Privada') and url.startswith('https://') and cidade and len(uf) == 2


def test_init_popula_catalogo_sem_duplicar(app):
    app.init_db()  # segunda execução: não pode duplicar nada
    with _db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM cursos_catalogo").fetchone()[0] == len(CURSOS)
        dup_fac = conn.execute("SELECT LOWER(nome), COUNT(*) FROM faculdades GROUP BY LOWER(nome) "
                               "HAVING COUNT(*) > 1").fetchall()
        assert dup_fac == []
        dup_cursos = conn.execute("SELECT LOWER(nome), faculdade_id, COUNT(*) FROM cursos "
                                  "GROUP BY LOWER(nome), faculdade_id HAVING COUNT(*) > 1").fetchall()
        assert dup_cursos == []
        assert conn.execute("SELECT COUNT(*) FROM cursos WHERE faculdade_id IS NULL").fetchone()[0] == 0
        esperadas = sum(len(c['ofertas']) for c in CURSOS)
        assert conn.execute("SELECT COUNT(*) FROM cursos").fetchone()[0] >= esperadas
        # O tipo do curso acompanha o da instituição
        divergentes = conn.execute("SELECT COUNT(*) FROM cursos c JOIN faculdades f ON f.id = c.faculdade_id "
                                   "WHERE c.tipo_instituicao <> f.tipo_instituicao").fetchone()[0]
        assert divergentes == 0


def test_catalogo_preserva_registros_existentes(app):
    """Uma nova versão do catálogo atualiza só o que veio do próprio
    catálogo e reaproveita a faculdade já cadastrada (sem duplicar)."""
    import database.catalogo_dados as dados
    from database.init_db import sincronizar_catalogo
    from config.database import get_connection

    with _db() as conn:
        usp_antes = conn.execute("SELECT id FROM faculdades WHERE sigla='USP'").fetchall()
        favoritos = conn.execute("SELECT COUNT(*) FROM cursos").fetchone()[0]
    versao = dados.CATALOGO_VERSAO
    try:
        dados.CATALOGO_VERSAO = versao + 1
        conn = get_connection()
        resumo = sincronizar_catalogo(conn)
        conn.close()
    finally:
        dados.CATALOGO_VERSAO = versao
    assert resumo == {'catalogo': 0, 'faculdades': 0, 'cursos': 0}
    with _db() as conn:
        assert conn.execute("SELECT id FROM faculdades WHERE sigla='USP'").fetchall() == usp_antes
        assert conn.execute("SELECT COUNT(*) FROM cursos").fetchone()[0] == favoritos


# ── API ──

def test_api_catalogo_lista_cursos_com_imagem_e_total(client):
    body = client.get('/api/cursos/catalogo').get_json()
    assert body['success'] is True
    assert len(body['cursos']) == len(CURSOS)
    por_nome = {c['nome']: c for c in body['cursos']}
    medicina = por_nome['Medicina']
    assert medicina['imagem_url'].startswith('https://images.unsplash.com/')
    assert medicina['total_instituicoes'] == len(next(c for c in CURSOS if c['nome'] == 'Medicina')['ofertas'])
    assert 'Saúde' in body['areas'] and 'Tecnologia' in body['areas']


def test_api_catalogo_filtra_por_area(client):
    body = client.get('/api/cursos/catalogo?area=Engenharias').get_json()
    assert body['cursos'] and all(c['area'] == 'Engenharias' for c in body['cursos'])


def test_novos_cursos_entram_na_busca_e_nos_filtros(client):
    sug = client.get('/api/busca/sugestoes?q=agrono&tipos=curso').get_json()['resultados']['curso']
    assert [s['valor'] for s in sug] == ['Agronomia']
    body = client.get('/api/cursos/listar?area=Ciências Exatas&limit=100').get_json()
    assert body['total'] > 0 and {c['nome'] for c in body['cursos']} >= {'Matemática', 'Física', 'Química'}
    body = client.get('/api/cursos/listar?modalidade=ead&limit=100').get_json()
    assert any(c['instituicao'].startswith('UNIVESP') for c in body['cursos'])


def test_faculdades_por_curso_exato(client):
    exato = client.get('/api/faculdades/listar?curso=Física&curso_exato=1&limit=50').get_json()
    contem = client.get('/api/faculdades/listar?curso=Física&limit=50').get_json()
    oferta_fisica = {o[0] for o in next(c for c in CURSOS if c['nome'] == 'Física')['ofertas']}
    assert {f['sigla'] for f in exato['faculdades']} == oferta_fisica
    # sem o parâmetro, continua a busca por parte do nome (traz Educação Física)
    assert contem['total'] > exato['total']


# ── Páginas ──

def test_home_tem_grade_de_cursos(client):
    html = client.get('/').get_data(as_text=True)
    assert 'id="cursos-lista-home"' in html and 'class="cursos-grade"' in html
    assert 'id="home-curso-busca"' in html


def test_pagina_cursos_lista_areas_do_banco(client):
    html = client.get('/cursos').get_data(as_text=True)
    for area in ('Engenharias', 'Humanas', 'Ciências Exatas', 'Todas as áreas'):
        assert f'>{area}</button>' in html


def test_cards_da_home_apontam_para_listagem_de_faculdades():
    js = open(os.path.join(RAIZ, 'public', 'js', 'home-cursos.js'), encoding='utf-8').read()
    assert '/faculdades?curso=${encodeURIComponent(curso.nome)}&exato=1' in js
    assert '/api/cursos/catalogo' in js
