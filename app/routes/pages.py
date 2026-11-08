"""Páginas HTML (Jinja2)."""
from flask import Blueprint, redirect, render_template, session, url_for

from app.models.faculdade import Faculdade
from app.models.vestibular import Vestibular
from app.security import admin_required, login_required
from app.services import dashboard_service, teste_vocacional_service
from app.services.erros import NaoEncontradoError

bp = Blueprint('pages', __name__)


@bp.route('/')
@bp.route('/home')
def home():
    return render_template(
        'home.html',
        proximos_vestibulares=Vestibular().proximos(limite=8),
        # IDs das faculdades em destaque, para o botão de favoritar
        faculdades_destaque=Faculdade().ids_por_sigla(['USP', 'FATEC', 'UNICAMP', 'UNIFESP']),
    )


@bp.route('/login')
def login():
    return render_template('login.html')


@bp.route('/cursos')
def cursos():
    return render_template('cursos.html')


@bp.route('/faculdades')
def faculdades():
    return render_template('faculdades.html')


@bp.route('/vestibulares')
def vestibulares():
    return render_template('vestibulares.html')


@bp.route('/testevocacional')
def testevocacional():
    return render_template('testevocacional.html', perguntas=teste_vocacional_service.perguntas_formulario())


@bp.route('/testevocacional/resultado')
def testevocacional_resultado():
    # A página é só a "casca": os dados vêm de /api/teste_vocacional/resultado
    # (prévia, pública) e /api/teste_vocacional/recomendacoes (exige login).
    return render_template('testevocacional_resultado.html', autenticado='user_id' in session)


@bp.route('/sobrenos')
def sobrenos():
    return render_template('sobrenos.html')


@bp.route('/ajuda')
def ajuda():
    return render_template('ajuda.html')


@bp.route('/verificar-email')
def verificar_email():
    return render_template('verificar-email.html')


@bp.route('/recuperar-senha')
def recuperar_senha():
    return render_template('recuperar-senha.html')


@bp.route('/favoritos')
def favoritos():
    if 'user_id' not in session:
        return redirect(url_for('pages.login'))
    return render_template('favoritos.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    try:
        dados = dashboard_service.resumo(session['user_id'])
    except NaoEncontradoError:
        # Conta removida enquanto a sessão ainda existia.
        session.clear()
        return redirect(url_for('pages.login'))
    return render_template('dashboard.html', **dados)


@bp.route('/admin')
@admin_required
def admin():
    return render_template('admin.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('pages.login'))
