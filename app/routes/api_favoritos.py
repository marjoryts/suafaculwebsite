"""API legada de favoritos (exige login). Regras em services/favorito_service.py."""
from flask import Blueprint, jsonify, request, session

from app.security import check_auth
from app.services import favorito_service

bp = Blueprint('api_favoritos', __name__, url_prefix='/api/favoritos')


@bp.route('/adicionar', methods=['POST'])
def adicionar():
    err = check_auth()
    if err:
        return err
    return jsonify(favorito_service.adicionar(
        session['user_id'], request.form.get('tipo', ''), request.form.get('item_id', 0),
        request.form.get('nome_item', '')))


@bp.route('/remover', methods=['POST'])
def remover():
    err = check_auth()
    if err:
        return err
    return jsonify(favorito_service.remover(
        session['user_id'], request.form.get('tipo', ''), request.form.get('item_id', 0)))


@bp.route('/listar', methods=['GET'])
def listar():
    err = check_auth()
    if err:
        return err
    return jsonify({'success': True,
                    'favoritos': favorito_service.listar(session['user_id'], request.args.get('tipo'))})


@bp.route('/verificar', methods=['GET'])
def verificar():
    err = check_auth()
    if err:
        return err
    return jsonify({'success': True, 'is_favorito': favorito_service.verificar(
        session['user_id'], request.args.get('tipo', ''), request.args.get('item_id', 0))})


@bp.route('/listar-ids', methods=['GET'])
def listar_ids():
    err = check_auth()
    if err:
        return err
    return jsonify({'success': True,
                    'ids': favorito_service.listar_ids(session['user_id'], request.args.get('tipo', ''))})
