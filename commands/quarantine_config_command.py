import discord
from discord.ext import commands
from discord import app_commands
from pymongo.errors import ConnectionFailure

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="config-quarentena", description="Configura o cargo e o canal de quarentena.")
    @app_commands.describe(cargo="O cargo de quarentena.", canal="O canal de quarentena.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def config_quarantine(interaction: discord.Interaction, cargo: discord.Role, canal: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        try:
            db = bot.db_client['guild_settings']
            settings_collection = db['quarantine_config']

            await settings_collection.update_one(
                {'guild_id': interaction.guild.id},
                {'$set': {
                    'quarantine_role_id': cargo.id,
                    'quarantine_channel_id': canal.id
                }},
                upsert=True
            )

            await interaction.followup.send(
                f"Configuração de quarentena salva com sucesso!\n"
                f"**Cargo:** {cargo.mention}\n"
                f"**Canal:** {canal.mention}"
            )

        except ConnectionFailure:
            await interaction.followup.send("Erro: Falha na conexão com o banco de dados. Por favor, tente novamente mais tarde.")
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao salvar a configuração: {e}")