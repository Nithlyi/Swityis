import discord
from discord.ext import commands
from discord import app_commands
import asyncio

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="quarentena", description="Move um usuário para um cargo/canal isolado para avaliação.")
    @app_commands.describe(usuario="O usuário a ser colocado em quarentena.", motivo="O motivo da quarentena.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def quarantine(interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)

        try:
            db = bot.db_client['guild_settings']
            settings_collection = db['quarantine_config']
            config = await settings_collection.find_one({'guild_id': interaction.guild.id})
            
            if not config:
                await interaction.followup.send("O sistema de quarentena não foi configurado para este servidor. Use `/config-quarentena` para configurá-lo.")
                return

            quarantine_role_id = config.get('quarantine_role_id')
            quarantine_role = interaction.guild.get_role(quarantine_role_id)

            if not quarantine_role:
                await interaction.followup.send("O cargo de quarentena configurado não foi encontrado. Verifique se ele ainda existe.")
                return

            # Guarda os IDs dos cargos atuais para restauração futura
            original_roles_ids = [r.id for r in usuario.roles if r.name != "@everyone" and r.id != quarantine_role_id]
            
            # Remove todos os cargos do usuário, exceto o @everyone, com delay
            roles_to_remove = [r for r in usuario.roles if r.name != "@everyone"]
            for role in roles_to_remove:
                try:
                    await usuario.remove_roles(role, reason=motivo)
                    await asyncio.sleep(0.5)  # Adiciona um delay de 0.5 segundos
                except discord.Forbidden:
                    await interaction.followup.send(f"Não tenho permissão para remover o cargo {role.name} de {usuario.display_name}.")
                    return
            
            # Adiciona o cargo de quarentena
            try:
                await usuario.add_roles(quarantine_role, reason=motivo)
            except discord.Forbidden:
                await interaction.followup.send(f"Não tenho permissão para adicionar o cargo de quarentena a {usuario.display_name}.")
                return

            # Salva os cargos originais no banco de dados
            users_collection = bot.db_client['users_data']
            await users_collection.update_one(
                {'user_id': usuario.id, 'guild_id': interaction.guild.id},
                {'$set': {'quarantine_roles': original_roles_ids}},
                upsert=True
            )

            quarantine_channel_id = config.get('quarantine_channel_id')
            if quarantine_channel_id and usuario.voice and usuario.voice.channel:
                quarantine_channel = bot.get_channel(quarantine_channel_id)
                if quarantine_channel:
                    await usuario.move_to(quarantine_channel, reason=motivo)
            
            await interaction.followup.send(
                f"✅ **{usuario.display_name}** foi colocado(a) em quarentena.\n**Motivo:** {motivo}"
            )
        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para gerenciar este cargo. Verifique a hierarquia de cargos.")
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro: {e}")