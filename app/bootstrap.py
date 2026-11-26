"""Passos de inicialização com efeito colateral (banco, seed).

Ficam fora de `create_app()` de propósito: importar o app não pode escrever
em disco nem iniciar threads (incompatível com execução serverless e
dificulta testes). Quem precisa deles chama estas funções explicitamente.
"""


def init_database(app=None):
    """Aplica migrations pendentes, dados de referência e o seed automático
    (idempotente). Ver database/init_db.py."""
    from database.init_db import init_db
    from app.services import seed_service
    init_db()
    seed_service.rodar_seed_automatico_se_necessario()
