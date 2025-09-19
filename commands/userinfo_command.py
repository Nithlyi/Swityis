import discord
from discord import app_commands, ui
from discord.ext import commands
import datetime

def setup(tree: app_commands.CommandTree, bot: commands.Bot):

    @tree.command(name="userinfo", description="Exibe informações detalhadas sobre um usuário.")
    @app_commands.describe(usuario="O usuário para obter as informações (opcional).")
    async def userinfo_command(interaction: discord.Interaction, usuario: discord.Member = None):
        """
        Exibe informações detalhadas sobre um usuário, como data de criação da conta e entrada no servidor.
        """
        await interaction.response.defer()

        target_user = usuario if usuario else interaction.user
        
        # Obter o cargo mais alto do usuário
        top_role = target_user.top_role
        
        # Formatar a data de criação da conta e de entrada no servidor
        account_created = discord.utils.format_dt(target_user.created_at, style='F')
        joined_server = discord.utils.format_dt(target_user.joined_at, style='F') if target_user.joined_at else "Não pôde ser determinado."
        
        # Contagem de cargos
        role_count = len(target_user.roles) - 1
        
        # Obter os cargos do usuário (excluindo @everyone)
        roles = [role.mention for role in sorted(target_user.roles, key=lambda role: role.position, reverse=True) if role.name != "@everyone"]
        
        embed = discord.Embed(
            title=f"Informações de {target_user.display_name}",
            description=f"Detalhes do usuário {target_user.mention}.",
            color=top_role.color if top_role.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.set_footer(text=f"ID do Usuário: {target_user.id}")
        
        embed.add_field(name="🌐 Nome de Usuário", value=target_user.name, inline=True)
        embed.add_field(name="🆔 ID", value=target_user.id, inline=True)
        embed.add_field(name="🔖 Nome de Exibição", value=target_user.display_name, inline=True)
        embed.add_field(name="⏰ Conta Criada Em", value=account_created, inline=True)
        embed.add_field(name="🎉 Entrou no Servidor Em", value=joined_server, inline=True)
        embed.add_field(name="🏷️ Cargo Mais Alto", value=top_role.mention, inline=True)

        # Limita o número de cargos exibidos
        if len(roles) > 20:
            roles = roles[:20]
            roles.append("...e mais")
        
        embed.add_field(name="🛡️ Cargos", value=" ".join(roles) if roles else "Nenhum cargo.", inline=False)

        await interaction.followup.send(embed=embed)
