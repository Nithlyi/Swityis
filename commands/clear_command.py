import discord
from discord.ext import commands
from discord import app_commands

class ClearCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="limpar", description="Limpa uma quantidade de mensagens do canal.")
    @app_commands.describe(quantidade="O número de mensagens a serem apagadas (máximo: 100).")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def limpar(self, interaction: discord.Interaction, quantidade: int):
        """Limpa uma quantidade de mensagens do canal."""
        if quantidade > 100 or quantidade < 1:
            await interaction.response.send_message("A quantidade de mensagens a serem apagadas deve ser entre 1 e 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            deleted_count = 0
            # Apaga as mensagens individualmente com delay
            async for message in interaction.channel.history(limit=quantidade + 1):
                if message.id != interaction.message.id:  # Evita apagar a mensagem do comando
                    await message.delete()
                    deleted_count += 1
                    await asyncio.sleep(0.5)  # Delay de 0.5 segundos

            # Envia uma mensagem de confirmação
            await interaction.followup.send(f"Foram apagadas {deleted_count} mensagens.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para gerenciar mensagens neste canal.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao tentar limpar as mensagens: {e}", ephemeral=True)

async def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    """Adiciona o comando de limpar à árvore de comandos."""
    cog = ClearCommand(bot)
    tree.add_command(cog.limpar)
