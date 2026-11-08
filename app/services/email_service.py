"""Envio de e-mails do SuaFacul (verificação de endereço, recuperação de senha e,
no futuro, avisos de segurança).

Configuração por variáveis de ambiente (nunca no código nem no app):

    EMAIL_MODO        smtp (padrão quando SMTP_HOST existe) | arquivo | memoria
    SMTP_HOST         ex.: smtp.gmail.com
    SMTP_PORTA        587 (STARTTLS, padrão) ou 465 (SSL)
    SMTP_USUARIO      ex.: suafacul.app@gmail.com
    SMTP_SENHA        no Gmail: "senha de app" (não a senha da conta)
    EMAIL_REMETENTE   opcional; padrão: "SuaFacul <SMTP_USUARIO>"

`arquivo` grava cada mensagem em database/emails_dev/ (ignorado pelo git) para
testar no computador sem servidor de e-mail; é recusado em produção (Vercel).
`memoria` é usado pelos testes automatizados.

Os logs registram só QUE um e-mail foi enviado (finalidade), nunca o conteúdo,
códigos ou senhas.
"""
import html
import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

log = logging.getLogger(__name__)

PASTA_ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'emails_dev')

# Caixa de saída do modo "memoria" (testes).
caixa_de_saida = []

ASSUNTOS = {
    'verificacao': 'Confirme seu e-mail no SuaFacul',
    'recuperacao': 'Código para redefinir sua senha do SuaFacul',
    'troca_email': 'Confirme seu novo e-mail no SuaFacul',
}

TEXTOS = {
    'verificacao': ('Confirme seu e-mail',
                    'Use o código abaixo para confirmar este endereço na sua conta do SuaFacul.'),
    'recuperacao': ('Redefinir sua senha',
                    'Recebemos um pedido para redefinir a senha da sua conta. Use o código abaixo no site ou no app.'),
    'troca_email': ('Confirme seu novo e-mail',
                    'Use o código abaixo para confirmar este endereço como o novo e-mail da sua conta.'),
}


class EmailNaoConfiguradoError(RuntimeError):
    pass


def _modo():
    modo = os.environ.get('EMAIL_MODO', '').strip().lower()
    if not modo:
        modo = 'smtp' if os.environ.get('SMTP_HOST') else ''
    return modo


def configurado():
    return _modo() in ('smtp', 'arquivo', 'memoria')


def _montar(destinatario, assunto, texto, corpo_html):
    usuario = os.environ.get('SMTP_USUARIO', '').strip()
    remetente = os.environ.get('EMAIL_REMETENTE', '').strip() or formataddr(('SuaFacul', usuario or 'nao-responda@suafacul.local'))
    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = remetente
    msg['To'] = destinatario
    msg['Message-ID'] = make_msgid(domain='suafacul')
    msg.set_content(texto)
    msg.add_alternative(corpo_html, subtype='html')
    return msg


def _enviar_smtp(msg):
    host = os.environ.get('SMTP_HOST', '').strip()
    porta = int(os.environ.get('SMTP_PORTA', '587') or 587)
    usuario = os.environ.get('SMTP_USUARIO', '').strip()
    senha = os.environ.get('SMTP_SENHA', '')
    if not host or not usuario or not senha:
        raise EmailNaoConfiguradoError('SMTP incompleto: defina SMTP_HOST, SMTP_USUARIO e SMTP_SENHA.')
    contexto = ssl.create_default_context()
    if porta == 465:
        with smtplib.SMTP_SSL(host, porta, context=contexto, timeout=20) as smtp:
            smtp.login(usuario, senha)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, porta, timeout=20) as smtp:
            smtp.starttls(context=contexto)
            smtp.login(usuario, senha)
            smtp.send_message(msg)


def _gravar_arquivo(msg):
    if os.environ.get('VERCEL'):
        raise EmailNaoConfiguradoError('EMAIL_MODO=arquivo é só para desenvolvimento local.')
    os.makedirs(PASTA_ARQUIVO, exist_ok=True)
    nome = datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.eml'
    with open(os.path.join(PASTA_ARQUIVO, nome), 'wb') as f:
        f.write(bytes(msg))


def enviar(destinatario, assunto, texto, corpo_html, finalidade='geral'):
    """Envia um e-mail. Devolve True se saiu; False se não há envio configurado ou falhou
    (o motivo vai para o log sem dados sensíveis)."""
    modo = _modo()
    if not modo:
        log.warning("[email] envio não configurado (defina SMTP_* ou EMAIL_MODO); e-mail de %s não enviado", finalidade)
        return False
    msg = _montar(destinatario, assunto, texto, corpo_html)
    try:
        if modo == 'memoria':
            caixa_de_saida.append(msg)
        elif modo == 'arquivo':
            _gravar_arquivo(msg)
        else:
            _enviar_smtp(msg)
    except Exception as e:  # SMTP fora do ar, credencial errada, etc.
        log.error("[email] falha ao enviar e-mail de %s: %s", finalidade, type(e).__name__)
        return False
    log.info("[email] e-mail de %s enviado", finalidade)
    return True


def _html_codigo(titulo, explicacao, codigo, nome, validade_min):
    caixas = ''.join(
        f'<td style="width:44px;height:52px;border-radius:12px;background:#ffffff;border:2px solid #5a189a;'
        f'font:700 26px Arial,sans-serif;color:#401a65;text-align:center">{html.escape(d)}</td><td style="width:8px"></td>'
        for d in codigo)
    saudacao = f'Olá, {html.escape(nome)}!' if nome else 'Olá!'
    return f"""<!doctype html>
<html lang="pt-br"><body style="margin:0;background:#f2f2f2;font-family:Arial,sans-serif;color:#262626">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f2f2;padding:24px 0">
    <tr><td align="center">
      <table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:20px;overflow:hidden">
        <tr><td style="background:#5a189a;padding:24px;text-align:center;font:700 28px Arial,sans-serif;color:#ffffff">Sua<span style="color:#ffa833">Facul</span></td></tr>
        <tr><td style="padding:28px 32px">
          <h1 style="margin:0 0 8px;font:700 22px Arial,sans-serif;color:#401a65">{html.escape(titulo)}</h1>
          <p style="margin:0 0 4px;font-size:15px">{saudacao}</p>
          <p style="margin:0 0 20px;font-size:15px;line-height:22px">{html.escape(explicacao)}</p>
          <table role="presentation" cellpadding="0" cellspacing="0" align="center"><tr>{caixas}</tr></table>
          <p style="margin:20px 0 0;font-size:14px;color:#757575;text-align:center">O código vale por {validade_min} minutos e só pode ser usado uma vez.</p>
          <p style="margin:20px 0 0;font-size:13px;color:#757575;line-height:20px">Se não foi você, ignore este e-mail: nada muda na sua conta.
          O SuaFacul nunca pede sua senha por e-mail.</p>
        </td></tr>
        <tr><td style="background:#ff9100;padding:12px;text-align:center;font-size:12px;color:#ffffff">SuaFacul · Seu futuro em um só lugar</td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def enviar_codigo(destinatario, finalidade, codigo, nome=None, validade_min=15):
    titulo, explicacao = TEXTOS[finalidade]
    texto = (f"{titulo}\n\n{explicacao}\n\nCódigo: {codigo}\n\n"
             f"O código vale por {validade_min} minutos e só pode ser usado uma vez.\n"
             "Se não foi você, ignore este e-mail. O SuaFacul nunca pede sua senha por e-mail.")
    return enviar(destinatario, ASSUNTOS[finalidade], texto,
                  _html_codigo(titulo, explicacao, codigo, nome, validade_min), finalidade)
