import discord
from discord.ext import commands
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="membro-suspeito", description="Analisa o histórico do usuário e dá um nível de risco.")
    @app_commands.describe(usuario="O usuário a ser analisado.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def suspicious_member(interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)

        # Esta é uma simulação, você precisará da sua lógica de banco de dados
        # Exemplo: busca punições, warns, etc.
        # punicoes = await bot.db_client.get_user_punishments(usuario.id)
        # warns = await bot.db_client.get_user_warnings(usuario.id)
        
        # Lógica para calcular o nível de risco (exemplo)
        # risk_level = len(punicoes) * 10 + len(warns) * 5

        # Simulação de dados
        risk_level = 75
        punishments = 3
        invites_found = True
        
        risk_text = "Baixo"
        if risk_level > 70:
            risk_text = "Alto"
        elif risk_level > 40:
            risk_text = "Médio"

        embed = discord.Embed(
            title=f"Análise de Risco de {usuario.display_name}",
            color=discord.Color.red() if risk_text == "Alto" else discord.Color.gold()
        )
        embed.add_field(name="Nível de Risco", value=risk_text, inline=False)
        embed.add_field(name="Punições Registradas", value=punishments, inline=False)
        embed.add_field(name="Convidado Encontrado?", value="Sim" if invites_found else "Não", inline=False)
        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else None)

        await interaction.followup.send(embed=embed)