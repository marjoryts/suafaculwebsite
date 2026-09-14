"""Testes do componente de rodapé padronizado: presença em todas as
páginas principais, ausência de duplicação, e responsividade básica
(classes/estrutura usadas pelo CSS responsivo)."""
import pytest

PAGINAS_PUBLICAS = ['/', '/cursos', '/faculdades', '/vestibulares', '/testevocacional', '/sobrenos']


@pytest.mark.parametrize('rota', PAGINAS_PUBLICAS)
def test_footer_presente_uma_unica_vez(client, rota):
    r = client.get(rota)
    assert r.status_code == 200
    html = r.data.decode()
    assert html.count('<footer>') == 1
    assert html.count('</footer>') == 1


@pytest.mark.parametrize('rota', PAGINAS_PUBLICAS)
def test_footer_usa_estrutura_responsiva(client, rota):
    html = client.get(rota).data.decode()
    assert 'footer-grid' in html
    assert 'footer-copyright' in html
    assert '/static/css/components/footer.css' in html


def test_footer_presente_em_paginas_logadas(admin_client):
    for rota in ('/dashboard', '/admin'):
        html = admin_client.get(rota).data.decode()
        assert html.count('<footer>') == 1, f"{rota} deveria ter exatamente um footer"


def test_footer_mostra_ano_atual(client):
    from datetime import date
    html = client.get('/').data.decode()
    assert str(date.today().year) in html
