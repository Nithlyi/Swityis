import discord
from discord.ext import commands
from discord import app_commands
import asyncio

async def handle_rate_limit(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limit atingido. Esperando...")
            await asyncio.sleep(e.retry_after)
            return await handle_rate_limit(func, *args, **kwargs)
        else:
            raise e

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

        clone_count = 0
        for name, members in name_map.items():
            if len(members) > 1:
                clones_found = True
                member_list = ", ".join([f"{m.display_name} ({m.id})" for m in members])
                
                # Limita o número de clones exibidos por mensagem
                if len(member_list) > 1024:
                    member_list = member_list[:1021] + "..."  # Trunca a lista se for muito longa
                
                embed.add_field(name=f"Nome Suspeito: '{name}'", value=member_list, inline=False)
                clone_count += 1
                
                if clone_count >= 20:  # Limita o número de campos no embed para evitar exceder o limite de tamanho
                    embed.add_field(name="Aviso", value="A lista de clones foi truncada para evitar exceder o limite de tamanho da mensagem.", inline=False)
                    break
        
        if not clones_found:
            embed.add_field(name="Resultado", value="Nenhum perfil suspeito de ser clone encontrado no servidor.")
        
        await handle_rate_limit(interaction.followup.send, embed=embed)