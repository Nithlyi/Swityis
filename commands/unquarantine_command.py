import discord
from discord.ext import commands
from discord import app_commands
import asyncio

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="liberar-quarentena", description="Remove um usuário da quarentena e restaura seus cargos.")
    @app_commands.describe(usuario="O usuário a ser liberado da quarentena.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def unquarantine(interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)

        try:
            # Pega o ID do cargo de quarentena
            db = bot.db_client['guild_settings']
            settings_collection = db['quarantine_config']
            config = await settings_collection.find_one({'guild_id': interaction.guild.id})
            
            if not config:
                await interaction.followup.send("O sistema de quarentena não foi configurado para este servidor.")
                return
            
            quarantine_role_id = config.get('quarantine_role_id')
            quarantine_role = interaction.guild.get_role(quarantine_role_id)
            
            # Pega os cargos originais do banco de dados
            users_collection = bot.db_client['users_data']
            user_data = await users_collection.find_one(
                {'user_id': usuario.id, 'guild_id': interaction.guild.id}
            )

            if not user_data or 'quarantine_roles' not in user_data:
                await interaction.followup.send(f"Não há dados de quarentena registrados para **{usuario.display_name}**.")
                return

            original_roles_ids = user_data.get('quarantine_roles', [])
            roles_to_add = [interaction.guild.get_role(role_id) for role_id in original_roles_ids if interaction.guild.get_role(role_id)]

            # Remove o cargo de quarentena e adiciona os cargos originais
            if quarantine_role in usuario.roles:
                await usuario.remove_roles(quarantine_role, reason="Quarentena removida.")
            
            if roles_to_add:
                await usuario.add_roles(*roles_to_add, reason="Cargos restaurados após quarentena.")

            # Limpa o registro do banco de dados para evitar lixo
            await users_collection.delete_one(
                {'user_id': usuario.id, 'guild_id': interaction.guild.id}
            )

            await interaction.followup.send(
                f"✅ **{usuario.display_name}** foi liberado(a) da quarentena e seus cargos foram restaurados."
            )

        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para gerenciar os cargos deste usuário.")
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro: {e}")