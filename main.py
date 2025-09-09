import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from database.database import setup_database
import asyncio
import logging

# Configura o logger
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
handler.setLevel(logging.INFO)

logging.getLogger('discord').addHandler(handler)
logging.getLogger('discord').setLevel(logging.INFO)

logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Importação dos módulos que contêm os comandos
from commands.antiraid_command import setup as setup_antiraid_command
from modules.personalization import Personalization
from utils.web_service import run_web_service
from commands.status_command import setup as setup_status_command
from utils.embed_creator import setup as setup_embed_creator
from modules.mod_panel import setup as setup_mod_panel
from modules.admin_panel import setup as setup_admin_panel
from modules.embed_panel import setup as setup_embed_panel
from modules.economy import setup as setup_economy
from modules.ticket_module import setup as setup_ticket_module
from modules.welcome_goodbye_module import setup as setup_welcome_goodbye_module
from modules.avatar_module import setup as setup_avatar_module
from commands.clear_command import setup as setup_clear_command
from commands.disable_command import setup as setup_disable_command
from commands.slowmode_command import setup as setup_slowmode_command
from commands.userinfo_command import setup as setup_userinfo_command
from commands.autorole_command import setup as setup_autorole_command
from modules.antispam_antilink import setup as setup_antispam_antilink_module
from commands.verify_command import setup as setup_verify_command
from commands.social_commands import setup as setup_social_commands

# MÓDULOS NOVOS DE SEGURANÇA
from modules.antinuke import AntiNuke
from modules.auto_quarantine import AutoQuarantine
from modules.audit_logs import AuditLogs # Importa o novo módulo de logs

# NOVOS COMANDOS CRIADOS JUNTOS
from commands.secret_room_command import setup as setup_secret_room_command
from commands.quarantine_command import setup as setup_quarantine_command
from commands.quarantine_config_command import setup as setup_quarantine_config_command
from commands.unquarantine_command import setup as setup_unquarantine_command
from commands.selective_clear_command import setup as setup_selective_clear_command
from commands.suspicious_member_command import setup as setup_suspicious_member_command
from commands.judgment_command import setup as setup_judgment_command
from commands.crime_file_command import setup as setup_crime_file_command
from commands.anti_clone_command import setup as setup_anti_clone_command
from commands.list_commands import setup as setup_list_commands
from commands.purge_commands import setup as setup_purge_commands
from commands.giveaway_command import setup as setup_giveaway_command
from modules.help_command import HelpCommand
from modules.backup_restore import BackupRestore

# ... seu código

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Carrega a configuração do arquivo JSON
with open('config.json', 'r') as f:
    config = json.load(f)

# Define as intents do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Cria a instância do bot
bot = commands.Bot(command_prefix='!', intents=intents)
bot.db_client = None
bot.logger = logger
bot.config = config

# -----------------
# FUNÇÕES DE CARREGAMENTO E SINCRONIZAÇÃO
# -----------------
async def load_modules():
    """Função para carregar todos os módulos de comandos."""
    bot.logger.info("Carregando módulos...")
    loaded_modules = 0

    try:
        # Módulos com cogs
        await bot.add_cog(Personalization(bot, bot.db_client))
        loaded_modules += 1
        await bot.add_cog(AntiNuke(bot))
        loaded_modules += 1
        await bot.add_cog(AutoQuarantine(bot))
        loaded_modules += 1
        await bot.add_cog(AuditLogs(bot)) # Linha para o novo módulo de logs
        loaded_modules += 1
        
        # Módulos que usam a função setup
        await setup_antiraid_command(bot.tree, bot, bot.db_client)
        loaded_modules += 1
        await setup_ticket_module(bot)
        loaded_modules += 1
        await setup_welcome_goodbye_module(bot)
        loaded_modules += 1
        await setup_economy(bot, bot.db_client)
        loaded_modules += 1
        await setup_avatar_module(bot)
        loaded_modules += 1
        await setup_clear_command(bot.tree, bot)
        loaded_modules += 1
        await setup_autorole_command(bot)
        loaded_modules += 1
        await setup_antispam_antilink_module(bot)
        loaded_modules += 1
        await setup_verify_command(bot)
        loaded_modules += 1
        await bot.add_cog(HelpCommand(bot))
        loaded_modules += 1
        await bot.add_cog(BackupRestore(bot))
        loaded_modules += 1







        
        # Módulos não assíncronos
        setup_status_command(bot.tree, bot, bot.db_client)
        loaded_modules += 1
        setup_embed_creator(bot.tree)
        loaded_modules += 1
        setup_mod_panel(bot.tree, config, bot.db_client)
        loaded_modules += 1
        setup_admin_panel(bot.tree, config, bot.db_client)
        loaded_modules += 1
        setup_embed_panel(bot.tree, bot)
        loaded_modules += 1
        setup_slowmode_command(bot.tree, bot)
        loaded_modules += 1
        setup_userinfo_command(bot.tree, bot)
        loaded_modules += 1
        
        # NOVOS COMANDOS CRIADOS JUNTOS
        setup_secret_room_command(bot.tree, bot)
        loaded_modules += 1
        setup_quarantine_command(bot.tree, bot)
        loaded_modules += 1
        setup_quarantine_config_command(bot.tree, bot)
        loaded_modules += 1
        setup_unquarantine_command(bot.tree, bot)
        loaded_modules += 1
        setup_selective_clear_command(bot.tree, bot)
        loaded_modules += 1
        setup_suspicious_member_command(bot.tree, bot)
        loaded_modules += 1
        setup_judgment_command(bot.tree, bot)
        loaded_modules += 1
        setup_crime_file_command(bot.tree, bot)
        loaded_modules += 1
        setup_anti_clone_command(bot.tree, bot)
        loaded_modules += 1
        setup_list_commands(bot.tree, bot, config)
        loaded_modules += 1
        setup_purge_commands(bot.tree, bot, config)
        loaded_modules += 1
        setup_giveaway_command(bot.tree, bot)
        loaded_modules += 1
        
        owner_id = config.get('owner_id')
        setup_social_commands(bot.tree, bot, owner_id)
        loaded_modules += 1
        
        if not owner_id:
            bot.logger.warning("ERRO: O ID do dono do bot não está configurado em config.json. O comando '/disable' não funcionará.")
        else:
            await setup_disable_command(bot, int(owner_id))
            loaded_modules += 1

        bot.logger.info(f"Carregamento concluído. {loaded_modules} módulos carregados com sucesso.")
    except Exception as e:
        bot.logger.error(f"Erro ao carregar os módulos: {e}")
        raise

async def sync_commands():
    """Sincroniza os comandos slash e exibe o status no console."""
    guild_id = config.get('guild_id')
    
    if not guild_id:
        bot.logger.warning("Aviso: Variável 'guild_id' não encontrada no config.json. Sincronizando comandos globalmente...")
        synced = await bot.tree.sync()
    else:
        bot.logger.info(f"Iniciando a sincronização de comandos para o servidor {guild_id}...")
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
    
    commands_synced = len(synced)
    bot.logger.info(f"\nSincronização concluída. {commands_synced} comandos sincronizados.")
    
    if commands_synced < 20:
        bot.logger.warning("Aviso: O número de comandos sincronizados é menor que o esperado (20). Verifique se todos os módulos estão sendo carregados corretamente.")

# -----------------
# EVENTOS DO BOT
# -----------------
@bot.event
async def on_ready():
    """Evento disparado quando o bot se conecta ao Discord."""
    bot.logger.info(f'Logado como {bot.user} (ID: {bot.user.id})')
    
    bot.logger.info("Conectando ao banco de dados...")
    bot.db_client = await setup_database()
    
    if not bot.db_client:
        bot.logger.error("Não foi possível conectar ao banco de dados. Encerrando o bot.")
        await bot.close()
        return
    
    try:
        await load_modules()
        await sync_commands()
        run_web_service(bot) 
        await bot.change_presence(activity=discord.Game(name="Online e operando!"))
        bot.logger.info("Web service iniciado.")
        bot.logger.info("Bot está pronto para operar.")
    except Exception as e:
        bot.logger.error(f"Ocorreu um erro fatal durante a inicialização do bot: {e}")
        await bot.close()

@bot.event
async def on_member_join(member: discord.Member):
    pass

@bot.event
async def on_member_remove(member: discord.Member):
    pass

# -----------------
# INICIA A EXECUÇÃO
# -----------------
if __name__ == "__main__":
    try:
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except KeyboardInterrupt:
        bot.logger.info("Bot encerrado manualmente.")