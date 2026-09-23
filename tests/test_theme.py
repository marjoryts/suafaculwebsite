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


@pytest.mark.parametrize('rota', ['/login', '/nao-existe-404'])
def test_paginas_sem_header_tambem_carregam_tema(client, rota):
    html = client.get(rota).data.decode()
    head = html.split('</head>')[0]
    assert '/static/js/theme.js' in head
    assert '/static/css/base.css' in head


def test_login_tem_botao_de_tema_flutuante(client):
    html = client.get('/login').data.decode()
    assert 'id="theme-toggle"' in html
    assert 'theme-toggle--floating' in html


def test_css_de_pagina_nao_redefine_root():
    """Um :root em CSS de página vence o .dark-mode do base.css (mesma
    especificidade, carregado depois) e desliga o modo noturno."""
    import glob, os, re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    arquivos = glob.glob(os.path.join(raiz, 'public', 'css', 'pages', '*.css')) + \
        glob.glob(os.path.join(raiz, 'public', 'css', 'components', '*.css'))
    assert arquivos
    for caminho in arquivos:
        css = re.sub(r'/\*.*?\*/', '', open(caminho, encoding='utf-8').read(), flags=re.S)
        assert ':root' not in css, f'{os.path.basename(caminho)} redefine :root'


def test_tokens_de_tema_definidos_nos_dois_temas():
    import os, re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css = open(os.path.join(raiz, 'public', 'css', 'base.css'), encoding='utf-8').read()
    root = css[css.index(':root {'):css.index('}', css.index(':root {'))]
    dark = css[css.index('.dark-mode {'):css.index('}', css.index('.dark-mode {'))]
    for token in ('--bg-color', '--surface-color', '--surface-muted', '--surface-hover',
                  '--surface-raised', '--field-bg', '--text-color', '--text-light',
                  '--heading-color', '--primary-text', '--border-color', '--field-border'):
        assert re.search(rf'{token}\s*:', root), f'{token} ausente no :root'
        assert re.search(rf'{token}\s*:', dark), f'{token} ausente no .dark-mode'
