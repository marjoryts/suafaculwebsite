"""Erros de negócio compartilhados pelos services.

Services levantam estas exceções; cada camada de entrada as traduz para o seu
formato: as rotas legadas devolvem {'success': False, 'message': ...} e a
futura API v1 devolverá o envelope estruturado {'error': {'code', 'message'}}.
"""


class ErroDeNegocio(Exception):
    """Base: regra de negócio violada (não é falha de infraestrutura)."""
    status = 400
    code = 'BUSINESS_RULE_VIOLATION'

    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details or {}


class ValidacaoError(ErroDeNegocio):
    status = 422
    code = 'VALIDATION_ERROR'


class NaoEncontradoError(ErroDeNegocio):
    status = 404
    code = 'RESOURCE_NOT_FOUND'


class ConflitoError(ErroDeNegocio):
    status = 409
    code = 'CONFLICT'


class NaoAutenticadoError(ErroDeNegocio):
    status = 401
    code = 'UNAUTHENTICATED'


class PermissaoNegadaError(ErroDeNegocio):
    status = 403
    code = 'FORBIDDEN'
