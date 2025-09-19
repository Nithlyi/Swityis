import discord
from discord import app_commands
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

logger = logging.getLogger(__name__)

async def handle_rate_limit(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limit atingido. Esperando...")
            await asyncio.sleep(e.retry_after)
            return await handle_rate_limit(func, *args, **kwargs)
        else:
            raise e


# Funções para o banco de dados
async def get_antiraid_config(db_client, guild_id):
    """Retorna a configuração antiraid do banco de dados para o servidor."""
    collection = db_client.mydatabase.antiraid_configs
    return await collection.find_one({"_id": guild_id}) or {
        "is_active": False,
        "kick_new_members": False,
        "ban_new_members": False,
        "required_account_age_days": 0,
        "raid_threshold": 10
    }

async def save_antiraid_config(db_client, guild_id, config):
    """Salva a configuração antiraid no banco de dados."""
    collection = db_client.mydatabase.antiraid_configs
    await collection.update_one(
        {"_id": guild_id},
        {"$set": config},
        upsert=True
    )

def create_antiraid_embed(config: dict) -> discord.Embed:
    """Cria um embed com o status atual das configurações de antiraid."""
    is_active = "✅ Ativo" if config.get("is_active") else "❌ Inativo"
    kick_new = "✅ Ativo" if config.get("kick_new_members") else "❌ Inativo"
    ban_new = "✅ Ativo" if config.get("ban_new_members") else "❌ Inativo"

    embed = discord.Embed(
        title="🛡️ Painel de Controle Antiraid",
        description=f"Status Geral: **{is_active}**\n\nUse os botões para configurar as proteções do servidor.",
        color=discord.Color.red() if config.get("is_active") else discord.Color.green()
    )

    embed.add_field(name="Opções de Proteção:", value=(
        f"> **Expulsar Contas Novas:** {kick_new}\n"
        f"> **Banir Contas Novas:** {ban_new}\n"
    ), inline=False)
    
    embed.add_field(name="Outras Configurações:", value=(
        f"> **Contas com Menos de (Dias):** {config.get('required_account_age_days')}\n"
        f"> **Limite de Entrada por Minuto:** {config.get('raid_threshold')}"
    ), inline=False)
    
    embed.set_footer(text="As mudanças são salvas automaticamente.")
    return embed

class AntiraidConfigView(discord.ui.View):
    def __init__(self, bot, db_client, guild_id, config):
        super().__init__(timeout=180)
        self.bot = bot
        self.db_client = db_client
        self.guild_id = guild_id
        self.config = config

    async def update_embed(self, interaction: discord.Interaction):
        new_embed = create_antiraid_embed(self.config)
        await interaction.response.edit_message(embed=new_embed, view=self)

    @discord.ui.button(label="Ativar/Desativar Antiraid", style=discord.ButtonStyle.danger)
    async def toggle_antiraid(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.config["is_active"] = not self.config.get("is_active")
        await save_antiraid_config(self.db_client, self.guild_id, self.config)
        await self.update_embed(interaction)

    @discord.ui.button(label="Expulsar Contas Novas", style=discord.ButtonStyle.secondary)
    async def toggle_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.config["kick_new_members"] = not self.config.get("kick_new_members")
        await save_antiraid_config(self.db_client, self.guild_id, self.config)
        await self.update_embed(interaction)

    @discord.ui.button(label="Banir Contas Novas", style=discord.ButtonStyle.secondary)
    async def toggle_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.config["ban_new_members"] = not self.config.get("ban_new_members")
        await save_antiraid_config(self.db_client, self.guild_id, self.config)
        await self.update_embed(interaction)

@app_commands.command(name="antiraid", description="Abre o painel de controle antiraid.")
@app_commands.checks.has_permissions(administrator=True)
async def antiraid(interaction: discord.Interaction):
    # Obtém a instância do bot e do cliente do banco de dados através da interação
    bot = interaction.client
    db_client = bot.db_client

    await interaction.response.defer(ephemeral=True, thinking=True)
    
    config = await get_antiraid_config(db_client, interaction.guild_id)
    
    view = AntiraidConfigView(bot, db_client, interaction.guild_id, config)
    embed = create_antiraid_embed(config)
    
    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(tree: app_commands.CommandTree, bot: commands.Bot, db_client: AsyncIOMotorClient):
    tree.add_command(antiraid)