import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from database.database import setup_database
import asyncio

# Importação dos módulos que contêm os comandos
from commands.antiraid_command import setup as setup_antiraid_command, get_antiraid_config
from modules.personalization import Personalization
from utils.web_service import run_web_service
from commands.status_command import setup as setup_status_command
from utils.embed_creator import setup as setup_embed_creator
from modules.mod_panel import setup as setup_mod_panel
from modules.admin_panel import setup as setup_admin_panel
from modules.embed_panel import setup as setup_embed_panel
from modules.economy import setup as setup_economy
from modules.ticket_module import setup as setup_ticket_module
from modules.avatar_module import setup as setup_avatar_module
from commands.clear_command import setup as setup_clear_command
from commands.disable_command import setup as setup_disable_command
from commands.slowmode_command import setup as setup_slowmode_command
from commands.userinfo_command import setup as setup_userinfo_command

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Carrega a configuração do arquivo JSON
with open('config.json', 'r') as f:
    config = json.load(f)

# Define as intents do bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Necessário para o comando /perfil e antiraid

# Cria a instância do bot e a árvore de comandos slash
bot = commands.Bot(command_prefix='!', intents=intents)
tree = bot.tree

# Conexão com o MongoDB. Agora é feita dentro da função main()
bot.db_client = None

@bot.event
async def on_ready():
    """Evento disparado quando o bot se conecta ao Discord."""
    print(f'Logado como {bot.user} (ID: {bot.user.id})')
    
    # Sincroniza os comandos slash e exibe o status no console
    await sync_commands()
    
    # Inicia o web service em uma thread separada
    run_web_service(bot) 
    
    # Define o status inicial do bot
    await bot.change_presence(activity=discord.Game(name="Online e operando!"))
    print("Web service iniciado.")

@bot.event
async def on_member_join(member: discord.Member):
    """Evento disparado quando um novo membro entra no servidor."""
    # --- Lógica do Antiraid ---
    if member.guild.me.guild_permissions.kick_members or member.guild.me.guild_permissions.ban_members:
        config = await get_antiraid_config(bot.db_client, member.guild.id)
        if config["is_active"]:
            required_age = config.get("required_account_age_days", 0)
            account_age = (discord.utils.utcnow() - member.created_at).days
            
            if required_age > 0 and account_age < required_age:
                if config.get("ban_new_members"):
                    try:
                        await member.ban(reason=f"Antiraid: Conta muito nova ({account_age} dias).")
                        print(f"Antiraid: Membro {member.name} banido por conta nova.")
                        return
                    except discord.Forbidden:
                        print(f"Antiraid: Sem permissão para banir o membro {member.name}.")
                
                if config.get("kick_new_members"):
                    try:
                        await member.kick(reason=f"Antiraid: Conta muito nova ({account_age} dias).")
                        print(f"Antiraid: Membro {member.name} expulso por conta nova.")
                        return
                    except discord.Forbidden:
                        print(f"Antiraid: Sem permissão para expulsar o membro {member.name}.")

@bot.event
async def on_member_remove(member: discord.Member):
    """Evento disparado quando um membro sai do servidor."""
    pass

async def sync_commands():
    """Sincroniza os comandos slash e exibe o status no console."""
    guild_id = config.get('guild_id')
    
    if not guild_id:
        print("Aviso: Variável 'guild_id' não encontrada no config.json. Sincronizando comandos globalmente...")
        synced = await bot.tree.sync()
    else:
        print(f"Iniciando a sincronização de comandos para o servidor {guild_id}...")
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
    
    commands_synced = len(synced)
    print(f"\nSincronização concluída. {commands_synced} comandos sincronizados.")
    
    if commands_synced < 20:
        print("Aviso: O número de comandos sincronizados é menor que o esperado (20). Verifique se todos os módulos estão sendo carregados corretamente.")


# -----------------
# INICIALIZAÇÃO E CARREGAMENTO DOS MÓDULOS
# -----------------
async def main():
    """Função principal para conectar ao banco de dados e iniciar o bot."""
    global db_client
    
    # Conecta ao banco de dados de forma assíncrona
    print("Conectando ao banco de dados...")
    db_client = await setup_database()
    if not db_client:
        print("Não foi possível conectar ao banco de dados. Encerrando o bot.")
        return

    # Seta o cliente do DB no objeto bot para fácil acesso em outros módulos
    bot.db_client = db_client
    
    # Inicia o bot
    await bot.start(os.getenv('DISCORD_BOT_TOKEN'))

@bot.event
async def on_connect():
    """
    Evento disparado quando o bot se conecta ao Discord.
    Aqui nós estabelecemos a conexão com o banco de dados
    e carregamos os módulos de comandos.
    """
    try:
        from database.database import setup_database
        bot.db_client = await setup_database()
        if not bot.db_client:
            print("Não foi possível conectar ao banco de dados. Encerrando o bot.")
            await bot.close()
            return
            
        owner_id = config.get('owner_id')
        if not owner_id:
            print("ERRO: O ID do dono do bot não está configurado em config.json. O comando '/disable' não funcionará.")
        else:
            await setup_disable_command(bot, int(owner_id))

        # Carrega os módulos
        await bot.add_cog(Personalization(bot, bot.db_client))
        await setup_antiraid_command(bot.tree, bot, bot.db_client)
        await setup_ticket_module(bot)
        await setup_economy(bot, bot.db_client)
        await setup_avatar_module(bot)
        await setup_clear_command(bot.tree, bot)
        setup_status_command(bot.tree, bot, bot.db_client)
        setup_embed_creator(bot.tree)
        setup_mod_panel(bot.tree, config, bot.db_client)
        setup_admin_panel(bot.tree, config, bot.db_client)
        setup_embed_panel(bot.tree, bot)
        setup_slowmode_command(bot.tree, bot)
        setup_userinfo_command(bot.tree, bot)
        

        print("Módulos de comandos carregados com sucesso.")

    except Exception as e:
        print(f"Erro ao carregar os módulos: {e}")
        await bot.close()

# Inicia a execução do programa
if __name__ == "__main__":
    try:
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except KeyboardInterrupt:
        print("Bot encerrado manualmente.")
