import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, TextStyle
from discord.ui import Modal, TextInput
from database.database import get_collection
import asyncio
import os

# Classes dos Modais (Pop-ups)
class VerifyConfigModal(Modal, title="Configurar Sistema de Verificação"):
    """
    Modal de configuração para o sistema de verificação.
    Permite ao administrador definir o canal, cargo, e o conteúdo do embed.
    """
    def __init__(self, guild_config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pré-preenche os campos do modal com os dados do banco de dados, se existirem
        self.verify_channel = TextInput(
            label="Canal do Painel (ID do Canal)",
            placeholder="ID do canal onde o painel será enviado",
            required=False,
            max_length=20,
            default=str(guild_config.get('channel_id', ''))
        )

        self.verify_role = TextInput(
            label="ID do Cargo de Verificação",
            placeholder="ID do cargo que o membro receberá (obrigatório)",
            required=True,
            max_length=20,
            default=str(guild_config.get('role_id', ''))
        )

        self.embed_title = TextInput(
            label="Título do Embed",
            placeholder="Verificação do Servidor!",
            required=False,
            max_length=256,
            default=guild_config.get('embed_title', 'Verificação do Servidor!')
        )

        self.embed_description = TextInput(
            label="Descrição do Embed",
            placeholder="Clique no botão para se verificar.",
            style=TextStyle.paragraph,
            required=False,
            max_length=4000,
            default=guild_config.get('embed_description', 'Clique no botão para se verificar.')
        )

        embed_color, embed_image_url = None, None
        if guild_config:
            embed_color = guild_config.get('embed_color')
            embed_image_url = guild_config.get('embed_image_url')
        
        default_color_image = ""
        if embed_color:
            default_color_image += f"#{embed_color:06X}"
        if embed_image_url:
            if default_color_image:
                default_color_image += " | "
            default_color_image += embed_image_url

        self.embed_color_and_image = TextInput(
            label="Cor e Imagem (opcional)",
            placeholder="#FFFFFF | URL_da_Imagem",
            required=False,
            max_length=2500,
            default=default_color_image
        )

        self.add_item(self.verify_channel)
        self.add_item(self.verify_role)
        self.add_item(self.embed_title)
        self.add_item(self.embed_description)
        self.add_item(self.embed_color_and_image)

    async def on_submit(self, interaction: discord.Interaction):
        """
        Salva as configurações do modal no banco de dados.
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id

        try:
            channel_id = int(self.verify_channel.value) if self.verify_channel.value.isdigit() else None
            role_id = int(self.verify_role.value) if self.verify_role.value.isdigit() else None
        except ValueError:
            await interaction.followup.send("❌ IDs de canal ou cargo inválidos. Use apenas números.", ephemeral=True)
            return

        if not role_id:
            await interaction.followup.send("❌ O ID do cargo de verificação é obrigatório.", ephemeral=True)
            return

        embed_color, embed_image_url = None, None
        if self.embed_color_and_image.value:
            parts = [part.strip() for part in self.embed_color_and_image.value.split('|')]
            
            # Tenta pegar a cor e a imagem, independentemente da ordem
            for part in parts:
                if part.startswith('#') and len(part) == 7:
                    try:
                        embed_color = int(part.replace('#', ''), 16)
                    except ValueError:
                        await interaction.followup.send("❌ Cor HEX inválida. Use o formato #FFFFFF.", ephemeral=True)
                        return
                elif part.startswith(('http://', 'https://')):
                    embed_image_url = part
            
        config_data = {
            'guild_id': guild_id,
            'channel_id': channel_id,
            'role_id': role_id,
            'embed_title': self.embed_title.value,
            'embed_description': self.embed_description.value,
            'embed_color': embed_color,
            'embed_image_url': embed_image_url,
            'panel_message_id': None
        }

        collection = get_collection(interaction.client.db_client, 'verify_configs')
        existing_config = await collection.find_one({'guild_id': guild_id})

        if existing_config:
            await collection.update_one({'guild_id': guild_id}, {'$set': config_data})
        else:
            await collection.insert_one(config_data)

        await interaction.followup.send("✅ Configurações de verificação salvas com sucesso! Use o botão 'Enviar Painel' para enviar o painel ao canal.", ephemeral=True)


# Classes dos Botões e View do painel de verificação
class VerifyButton(ui.Button):
    """Botão para o membro se verificar."""
    def __init__(self, bot):
        super().__init__(label="Verificar-se", style=ButtonStyle.green, custom_id="verify_button")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        collection = get_collection(self.bot.db_client, 'verify_configs')
        guild_config = await collection.find_one({'guild_id': interaction.guild.id})

        if not guild_config or not guild_config.get('role_id'):
            await interaction.followup.send("❌ O sistema de verificação não está configurado neste servidor ou o cargo não foi definido.", ephemeral=True)
            return

        role = interaction.guild.get_role(guild_config['role_id'])
        if not role:
            await interaction.followup.send("❌ O cargo de verificação não foi encontrado. Por favor, verifique se o ID está correto ou se o cargo não foi excluído.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            await asyncio.sleep(0.5)  # Adiciona um delay de 0.5 segundos
            await interaction.followup.send("✅ Você foi verificado(a) com sucesso!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Não tenho permissão para adicionar este cargo. Por favor, verifique minhas permissões no servidor.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ocorreu um erro inesperado: {e}", ephemeral=True)


class VerifyView(ui.View):
    """View contendo o botão de verificação. É persistente."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(VerifyButton(self.bot))


# Classes dos Botões do Painel de Configuração
class ConfigButton(ui.Button):
    """Botão para abrir o modal de configuração."""
    def __init__(self, bot):
        super().__init__(label="Configurar Verificação", style=ButtonStyle.primary, custom_id="config_verify_button")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        collection = get_collection(self.bot.db_client, 'verify_configs')
        guild_config = await collection.find_one({'guild_id': interaction.guild.id})
        await interaction.response.send_modal(VerifyConfigModal(guild_config or {}))


class SendPanelButton(ui.Button):
    """Botão para enviar o painel de verificação ao canal configurado."""
    def __init__(self, bot):
        super().__init__(label="Enviar Painel", style=ButtonStyle.green, custom_id="send_verify_panel_button")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        collection = get_collection(self.bot.db_client, 'verify_configs')
        guild_config = await collection.find_one({'guild_id': interaction.guild.id})

        if not guild_config:
            await interaction.followup.send("❌ Nenhuma configuração de verificação encontrada. Por favor, configure o painel primeiro.", ephemeral=True)
            return

        channel_id = guild_config.get('channel_id')
        channel = interaction.guild.get_channel(channel_id) if channel_id else interaction.channel

        if not channel:
            await interaction.followup.send("❌ Canal não encontrado. Por favor, verifique o ID do canal ou tente novamente.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=guild_config.get('embed_title'),
            description=guild_config.get('embed_description'),
            color=guild_config.get('embed_color') or discord.Color.blue()
        )
        if guild_config.get('embed_image_url'):
            embed.set_image(url=guild_config.get('embed_image_url'))

        verify_view = VerifyView(self.bot)
    
        if guild_config.get('panel_message_id'):
            try:
                old_message = await channel.fetch_message(guild_config.get('panel_message_id'))
                await old_message.delete()
            except (discord.NotFound, discord.Forbidden, AttributeError):
                # Ignora se a mensagem não for encontrada ou se o bot não tiver permissão para excluir
                pass

        try:
            new_message = await channel.send(embed=embed, view=verify_view)
            await collection.update_one({'guild_id': interaction.guild.id}, {'$set': {'panel_message_id': new_message.id}})
            await interaction.followup.send(f"✅ Painel de verificação enviado para {channel.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Não tenho permissão para enviar mensagens neste canal.", ephemeral=True)


class RemoveButton(ui.Button):
    """Botão para remover o sistema de verificação."""
    def __init__(self, bot):
        super().__init__(label="Remover Verificação", style=ButtonStyle.danger, custom_id="remove_verify_button")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        collection = get_collection(self.bot.db_client, 'verify_configs')
        existing_config = await collection.find_one({'guild_id': interaction.guild.id})

        if existing_config:
            try:
                channel = interaction.guild.get_channel(existing_config.get('channel_id'))
                if channel:
                    message = await channel.fetch_message(existing_config.get('panel_message_id'))
                    await message.delete()
            except (discord.NotFound, discord.Forbidden, AttributeError):
                pass
            
            await collection.delete_one({'guild_id': interaction.guild.id})
            await interaction.followup.send("✅ Sistema de verificação removido com sucesso.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Não há sistema de verificação para remover.", ephemeral=True)


class ConfigPanelView(ui.View):
    """View contendo os botões de configuração. É persistente."""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(ConfigButton(bot))
        self.add_item(SendPanelButton(bot))
        self.add_item(RemoveButton(bot))


# Classe Principal (Cog)
class VerifyModule(commands.Cog):
    """
    Cog principal para o módulo de verificação.
    Contém o comando de barra para criar o painel de configuração.
    """
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="painel_verificar", description="Cria um painel para configurar o sistema de verificação do servidor.")
    @app_commands.default_permissions(manage_channels=True)
    async def create_config_panel(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed(
            title="Painel de Configuração - Verificação",
            description="Use os botões abaixo para gerenciar o sistema de verificação.",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, view=ConfigPanelView(self.bot))


async def setup(bot: commands.Bot):
    """Função de configuração que adiciona a cog e as views persistentes."""
    await bot.add_cog(VerifyModule(bot))
    bot.add_view(VerifyView(bot))
    bot.add_view(ConfigPanelView(bot))
