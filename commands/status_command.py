import discord
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: discord.Client, db_client):
    """Seta o comando slash de status."""
    
    # Exemplo de comando
    # db = db_client.seu_banco.sua_colecao # Exemplo de uso do DB
    
    @tree.command(name="status", description="Altera o status do bot.")
    @app_commands.describe(novo_status="O novo status para o bot.")
    async def change_status(interaction: discord.Interaction, novo_status: str):
        """Altera o status de atividade do bot."""
        await bot.change_presence(activity=discord.Game(name=novo_status))
        await interaction.response.send_message(f"Status do bot alterado para: **{novo_status}**.", ephemeral=True)