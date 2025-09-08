import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.app_commands import checks

def setup(tree: app_commands.CommandTree, bot: commands.Bot):

    @tree.command(name="slowmode", description="Define o modo lento para um canal.")
    @checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        canal="O canal de texto a ser configurado (opcional, padrão é o canal atual).",
        segundos="O tempo do modo lento em segundos (0 para desativar)."
    )
    async def slowmode_command(interaction: discord.Interaction, segundos: int, canal: discord.TextChannel = None):
        """
        Define o modo lento para um canal.
        """
        await interaction.response.defer(ephemeral=True)
        
        target_channel = canal if canal else interaction.channel

        if not isinstance(target_channel, discord.TextChannel):
            await interaction.followup.send("Este comando só pode ser usado em um canal de texto.", ephemeral=True)
            return

        try:
            await target_channel.edit(slowmode_delay=segundos)
            await interaction.followup.send(f"Modo lento do canal {target_channel.mention} foi definido para `{segundos}` segundos.", ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para gerenciar canais. Por favor, verifique minhas permissões.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro: {e}", ephemeral=True)
