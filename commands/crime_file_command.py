import discord
from discord.ext import commands
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="ficha-criminal", description="Mostra todas as punições de um usuário.")
    @app_commands.describe(usuario="O usuário para ver a ficha criminal.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def crime_file(interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)

        # Simulação de dados do banco de dados
        # Punições reais devem ser obtidas do seu bot.db_client
        punishments = [
            {"tipo": "Mute", "motivo": "Spam de links", "data": "2024-05-10"},
            {"tipo": "Warn", "motivo": "Linguagem imprópria", "data": "2024-06-21"},
            {"tipo": "Kick", "motivo": "Comportamento abusivo", "data": "2024-07-01"}
        ]
        
        if not punishments:
            await interaction.followup.send(f"A ficha criminal de {usuario.mention} está limpa.")
            return

        embed = discord.Embed(
            title=f"Ficha Criminal de {usuario.display_name}",
            color=discord.Color.dark_red()
        )
        embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else None)

        punishment_count = 0
        for punishment in punishments:
            embed.add_field(
                name=f"{punishment['tipo']} - {punishment['data']}",
                value=f"**Motivo:** {punishment['motivo']}",
                inline=False
            )
            punishment_count += 1
            
            if punishment_count >= 20:  # Limita o número de punições exibidas para evitar exceder o limite de tamanho da mensagem
                embed.add_field(name="Aviso", value="A lista de punições foi truncada para evitar exceder o limite de tamanho da mensagem.", inline=False)
                break
        
        await interaction.followup.send(embed=embed)