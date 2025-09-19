import discord
from discord.ext import commands
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="limpeza-seletiva", description="Apaga mensagens que contêm uma palavra específica.")
    @app_commands.describe(palavra="A palavra a ser buscada nas mensagens.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def selective_clear(interaction: discord.Interaction, palavra: str):
        await interaction.response.defer(ephemeral=True) # Defer a resposta para não dar timeout

        deleted_count = 0
        async for message in interaction.channel.history(limit=200): # Limite de 200 mensagens
            if palavra.lower() in message.content.lower():
                try:
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # Adiciona um delay de 0.5 segundos
                except discord.NotFound:
                    pass
        
        await interaction.followup.send(f"Foram apagadas {deleted_count} mensagens que continham a palavra '{palavra}'.")