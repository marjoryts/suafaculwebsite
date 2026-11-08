"""Dados da requisição usados pelos limites de abuso (site e app)."""
import os

from flask import request


def ip_cliente():
    """IP de quem fez a requisição. Na Vercel o app fica atrás do proxy dela, que
    informa o IP real no X-Forwarded-For (o primeiro da lista). Fora da Vercel o
    cabeçalho é ignorado: qualquer cliente poderia forjá-lo para escapar do limite."""
    if os.environ.get('VERCEL'):
        encaminhado = request.headers.get('X-Forwarded-For', '')
        if encaminhado:
            return encaminhado.split(',')[0].strip()
    return request.remote_addr or ''
