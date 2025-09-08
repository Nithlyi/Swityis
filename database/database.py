import motor.motor_asyncio
import os
import logging

# Configuração de logging para este módulo
logger = logging.getLogger(__name__)

async def setup_database():
    """Conecta ao MongoDB usando a biblioteca motor para operações assíncronas."""
    try:
        uri = os.getenv('MONGO_URI')
        if not uri:
            raise ValueError("A variável de ambiente 'MONGO_URI' não está definida.")
        
        # Cria uma instância do cliente assíncrono do MongoDB
        client = motor.motor_asyncio.AsyncIOMotorClient(uri)

        # O comando client.admin.command('ping') verifica a conexão
        await client.admin.command('ping')
        logger.info("Conectado ao MongoDB com sucesso!")
        return client
    except Exception as e:
        logger.error(f"Erro ao conectar ao MongoDB: {e}")
        return None

def get_collection(client, collection_name: str):
    """
    Retorna uma coleção específica do banco de dados.
    Args:
        client: O cliente do MongoDB.
        collection_name: O nome da coleção a ser retornada.
    """
    db = client.get_database("bot_data")
    return db.get_collection(collection_name)
