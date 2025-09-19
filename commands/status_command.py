import discord
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: discord.Client, db_client):
    """Seta o comando slash de status."""
    
    # Exemplo de comando
    # db = db_client.seu_banco.sua_colecao # Exemplo de uso do DB
    
    @tree.command(name="status", description="Altera o status do bot.")
    @app_commands.describe(novo_status="O novo status para o bot.")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def change_status(interaction: discord.Interaction, novo_status: str):
        """Altera o status de atividade do bot."""
        await bot.change_presence(activity=discord.Game(name=novo_status))
        await interaction.response.send_message(f"Status do bot alterado para: **{novo_status}**.", ephemeral=True)

    @change_status.error
    async def change_status_error(interaction: discord.Interaction, error):
        if isinstance(error, commands.CommandOnCooldown):
            await interaction.response.send_message(f"Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.", ephemeral=True)
        else:
            raise error