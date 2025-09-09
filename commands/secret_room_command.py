import discord
from discord.ext import commands
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="sala-secreta", description="Move um usuário para um canal secreto para conversa com mods.")
    @app_commands.describe(usuario="O usuário a ser movido para a sala secreta.")
    @app_commands.checks.has_permissions(move_members=True)
    async def secret_room(interaction: discord.Interaction, usuario: discord.Member):
        # Substitua com os IDs dos canais e cargos
        MOD_ROLE_ID = 123456789012345678 # ID do cargo de moderador
        SECRET_CHANNEL_ID = 123456789012345679 # ID do canal secreto

        mod_role = discord.utils.get(interaction.guild.roles, id=MOD_ROLE_ID)
        secret_channel = bot.get_channel(SECRET_CHANNEL_ID)

        if not mod_role:
            await interaction.response.send_message("O cargo de moderador não foi encontrado.", ephemeral=True)
            return
        
        if not secret_channel:
            await interaction.response.send_message("O canal secreto não foi encontrado.", ephemeral=True)
            return

        # Verifica se o usuário tem a permissão de moderador
        if not interaction.user.guild_permissions.move_members:
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        # Verifica se o usuário está em um canal de voz
        if usuario.voice and usuario.voice.channel:
            await usuario.move_to(secret_channel, reason="Movido para sala secreta por um moderador.")
            await interaction.response.send_message(
                f"{usuario.mention} foi movido para a sala secreta para conversar com a moderação.", 
                ephemeral=False
            )
        else:
            await interaction.response.send_message(f"{usuario.mention} não está em um canal de voz.", ephemeral=True)