import discord
from discord.ext import commands
from discord import app_commands

def is_owner_check(config):
    """Cria uma verificação que retorna True se o usuário for o dono do bot."""
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == int(config.get('owner_id'))
    return app_commands.check(predicate)

def setup(tree: app_commands.CommandTree, bot: commands.Bot, config: dict):
    @tree.command(name="purge-commands", description="Limpa e ressincroniza todos os comandos slash globalmente.")
    @is_owner_check(config)
    async def purge_commands(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        bot.tree.clear_commands(guild=None)
        await interaction.followup.send("Comandos globais limpos. Sincronizando...")
        synced = await bot.tree.sync()

        await interaction.followup.send(f"Limpeza e ressincronização concluídas com sucesso! {len(synced)} comandos sincronizados.")