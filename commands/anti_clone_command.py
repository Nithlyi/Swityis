import discord
from discord.ext import commands
from discord import app_commands

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="anti-clone", description="Analisa perfis com nomes e avatares semelhantes.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def anti_clone(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Relatório Anti-Clone",
            color=discord.Color.blue()
        )
        
        clones_found = False
        
        # Dicionário para agrupar membros por nome (case-insensitive)
        name_map = {}
        for member in interaction.guild.members:
            lower_name = member.name.lower()
            if lower_name not in name_map:
                name_map[lower_name] = []
            name_map[lower_name].append(member)

        for name, members in name_map.items():
            if len(members) > 1:
                clones_found = True
                member_list = ", ".join([f"{m.display_name} ({m.id})" for m in members])
                embed.add_field(name=f"Nome Suspeito: '{name}'", value=member_list, inline=False)
        
        if not clones_found:
            embed.add_field(name="Resultado", value="Nenhum perfil suspeito de ser clone encontrado no servidor.")
            
        await interaction.followup.send(embed=embed)