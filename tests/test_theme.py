"""Testes do modo noturno: botão de tema no header e script de tema
carregado no <head> (antes do <body>, para evitar o "flash" de tema claro)."""
import pytest

PAGINAS_PUBLICAS = ['/', '/cursos', '/faculdades', '/vestibulares', '/testevocacional', '/sobrenos', '/ajuda']


@pytest.mark.parametrize('rota', PAGINAS_PUBLICAS)
def test_header_tem_botao_de_tema(client, rota):
    html = client.get(rota).data.decode()
    assert html.count('id="theme-toggle"') == 1
    assert 'fa-moon' in html and 'fa-sun' in html


@pytest.mark.parametrize('rota', PAGINAS_PUBLICAS)
def test_script_de_tema_carregado_no_head(client, rota):
    html = client.get(rota).data.decode()
    head = html.split('</head>')[0]
    assert '/static/js/theme.js' in head


def test_tema_em_paginas_logadas(admin_client):
    for rota in ('/dashboard', '/admin'):
        html = admin_client.get(rota).data.decode()
        assert 'id="theme-toggle"' in html, rota
        assert '/static/js/theme.js' in html.split('</head>')[0], rota
