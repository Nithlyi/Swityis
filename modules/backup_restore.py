import discord
from discord.ext import commands
from discord import app_commands
import json
import io

class BackupRestore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="backup", description="[DONO] Faz um backup da estrutura do servidor e envia um arquivo.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def backup_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="Confirmação de Backup",
            description="Você tem certeza que deseja criar um backup da estrutura do servidor? Um arquivo JSON será enviado para a sua DM.",
            color=discord.Color.blue()
        )
        
        view = discord.ui.View()
        confirm_button = discord.ui.Button(label="Sim", style=discord.ButtonStyle.success)
        cancel_button = discord.ui.Button(label="Não", style=discord.ButtonStyle.danger)

        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await self._perform_backup(interaction)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Operação de backup cancelada.", embed=None, view=None)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    async def _perform_backup(self, interaction: discord.Interaction):
        guild = interaction.guild
        backup_data = {
            "name": guild.name,
            "roles": [],
            "channels": []
        }

        # 1. Back up de Cargos
        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            backup_data["roles"].append({
                "name": role.name,
                "permissions": role.permissions.value,
                "color": str(role.color),
                "mentionable": role.mentionable,
                "hoist": role.hoist
            })

        # 2. Back up de Canais e Categorias
        for category in guild.categories:
            category_data = {
                "name": category.name,
                "type": "category",
                "position": category.position,
                "permission_overwrites": []
            }
            # Permissões da Categoria
            for overwrite in category.overwrites:
                category_data["permission_overwrites"].append({
                    "id": overwrite.id,
                    "type": "role" if isinstance(overwrite, discord.Role) else "member",
                    "allow": overwrite.pair[0].value,
                    "deny": overwrite.pair[1].value
                })
            
            # Canais dentro da Categoria
            category_channels = []
            for channel in category.channels:
                channel_data = {
                    "name": channel.name,
                    "position": channel.position
                }
                if isinstance(channel, discord.TextChannel):
                    channel_data["type"] = "text"
                    channel_data["topic"] = channel.topic
                elif isinstance(channel, discord.VoiceChannel):
                    channel_data["type"] = "voice"
                    channel_data["user_limit"] = channel.user_limit
                
                category_channels.append(channel_data)

            category_data["channels"] = category_channels
            backup_data["channels"].append(category_data)

        # 3. Back up de Canais sem Categoria
        for channel in guild.channels:
            if channel.category is None:
                channel_data = {
                    "name": channel.name,
                    "type": "text" if isinstance(channel, discord.TextChannel) else "voice",
                    "position": channel.position
                }
                if isinstance(channel, discord.TextChannel):
                    channel_data["topic"] = channel.topic
                elif isinstance(channel, discord.VoiceChannel):
                    channel_data["user_limit"] = channel.user_limit

                backup_data["channels"].append(channel_data)

        # 4. Cria o arquivo JSON
        file_content = json.dumps(backup_data, indent=4)
        file = discord.File(io.StringIO(file_content), filename=f"backup-{guild.id}.json")

        await interaction.followup.send(
            content="✅ Backup concluído! O arquivo foi enviado para a sua DM por segurança.", 
            ephemeral=True
        )
        await interaction.user.send("Aqui está o arquivo de backup do seu servidor:", file=file)

    @app_commands.command(name="restaurar", description="[DONO] Restaura o servidor a partir de um arquivo de backup.")
    @app_commands.guild_only()
    async def restore_command(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id != interaction.guild.owner_id:
            await interaction.followup.send("❌ Apenas o dono do servidor pode usar este comando.", ephemeral=True)
            return

        if not file or not file.filename.endswith(".json"):
            await interaction.followup.send("❌ Por favor, anexe um arquivo de backup no formato JSON (.json).", ephemeral=True)
            return

        try:
            backup_data = json.loads(await file.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            await interaction.followup.send("❌ Ocorreu um erro ao ler o arquivo. Certifique-se de que é um arquivo JSON válido.", ephemeral=True)
            return

        # Confirmação da ação
        embed = discord.Embed(
            title="⚠️ Aviso Importante",
            description="Você está prestes a **deletar todos os canais e cargos** deste servidor e recriá-los a partir do arquivo de backup.\n\n**Esta ação é irreversível.**\n\nConfirme para continuar.",
            color=discord.Color.red()
        )
        
        view = discord.ui.View()
        confirm_button = discord.ui.Button(label="Sim", style=discord.ButtonStyle.danger)
        cancel_button = discord.ui.Button(label="Não", style=discord.ButtonStyle.secondary)
        
        async def confirm_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await self._perform_restore(interaction, backup_data)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Operação de restauração cancelada.", embed=None, view=None)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _perform_restore(self, interaction: discord.Interaction, backup_data):
        guild = interaction.guild
        
        # O envio da primeira mensagem
        await interaction.followup.send("Iniciando a restauração... Apagando canais e cargos existentes.", ephemeral=True)

        # Apagar todos os canais e categorias
        for channel in guild.channels:
            try:
                await channel.delete()
            except discord.errors.NotFound:
                pass
        
        # Apagar todos os cargos (exceto o @everyone e o cargo do bot)
        for role in guild.roles:
            if role.name != "@everyone" and not role.is_bot_managed():
                try:
                    await role.delete()
                except discord.Forbidden:
                    pass

        # Restaurar Cargos
        restored_roles = {}
        for role_data in backup_data["roles"]:
            try:
                new_role = await guild.create_role(
                    name=role_data["name"],
                    permissions=discord.Permissions(role_data["permissions"]),
                    color=discord.Color(int(role_data["color"].replace("#", ""), 16)),
                    mentionable=role_data["mentionable"],
                    hoist=role_data["hoist"]
                )
                restored_roles[role_data["name"]] = new_role
            except discord.Forbidden:
                pass

        # Restaurar Canais e Categorias
        for channel_data in backup_data["channels"]:
            if channel_data["type"] == "category":
                new_category = await guild.create_category(
                    name=channel_data["name"],
                    position=channel_data["position"]
                )
                # Criar canais dentro da categoria
                for sub_channel_data in channel_data.get("channels", []):
                    if sub_channel_data["type"] == "text":
                        await guild.create_text_channel(
                            name=sub_channel_data["name"],
                            category=new_category,
                            position=sub_channel_data.get("position", 0),
                            topic=sub_channel_data.get("topic")
                        )
                    elif sub_channel_data["type"] == "voice":
                        await guild.create_voice_channel(
                            name=sub_channel_data["name"],
                            category=new_category,
                            position=sub_channel_data.get("position", 0),
                            user_limit=sub_channel_data.get("user_limit")
                        )
            else:
                # Criar canais sem categoria
                if channel_data["type"] == "text":
                    await guild.create_text_channel(
                        name=channel_data["name"],
                        position=channel_data.get("position", 0),
                        topic=channel_data.get("topic")
                    )
                elif channel_data["type"] == "voice":
                    await guild.create_voice_channel(
                        name=channel_data["name"],
                        position=channel_data.get("position", 0),
                        user_limit=channel_data.get("user_limit")
                    )
        
        # O envio da segunda e última mensagem
        try:
            await interaction.followup.send("✅ Restauração concluída! A estrutura do servidor foi restaurada com sucesso.", ephemeral=True)
        except discord.errors.HTTPException:
            # Caso o canal já tenha sido apagado, o bot não pode responder, mas a restauração foi concluída
            pass

async def setup(bot):
    await bot.add_cog(BackupRestore(bot))
    print("Módulo de Backup e Restauração carregado.")