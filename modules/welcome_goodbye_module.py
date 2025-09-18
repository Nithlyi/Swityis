import discord
from discord.ext import commands
from discord import app_commands, ui, TextStyle
from database.database import get_collection
from discord.ui import Modal, TextInput
from discord.errors import Forbidden

# -----------------
# CLASSES MODAIS
# -----------------
class WelcomeModal(Modal, title="Configurar Mensagem de Boas-Vindas"):
    
    welcome_channel = TextInput(
        label="Canal da Mensagem (ID do Canal)",
        placeholder="ID do canal onde a mensagem será enviada",
        required=True,
        max_length=20
    )

    welcome_title = TextInput(
        label="Título do Embed",
        placeholder="Boas-vindas ao servidor!",
        required=False,
        max_length=256
    )

    welcome_description = TextInput(
        label="Descrição do Embed",
        placeholder="Boas-vindas, {user}! Esperamos que você goste do nosso servidor.",
        style=TextStyle.paragraph,
        required=False,
        max_length=4000
    )

    welcome_footer = TextInput(
        label="Rodapé do Embed",
        placeholder="Desenvolvido por [Seu Bot]",
        required=False,
        max_length=2048
    )

    welcome_extras = TextInput(
        label="Cor (HEX) e Imagem (URL)",
        placeholder="Exemplo: #FF0000 | https://sua-imagem.com/imagem.png",
        required=False,
        max_length=2048
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id
        
        # Coleta os dados do modal
        try:
            channel_id = int(self.welcome_channel.value)
        except ValueError:
            await interaction.followup.send("❌ O ID do canal deve ser um número válido.", ephemeral=True)
            return

        welcome_data = {
            'welcome_title': self.welcome_title.value,
            'welcome_description': self.welcome_description.value,
            'welcome_footer': self.welcome_footer.value
        }

        # Analisa o campo 'welcome_extras'
        extras = [part.strip() for part in self.welcome_extras.value.split('|')]
        welcome_data['welcome_color'] = extras[0] if len(extras) > 0 and extras[0].startswith('#') else None
        welcome_data['welcome_image_url'] = extras[1] if len(extras) > 1 and extras[1].startswith('http') else None

        # Armazena os dados no banco de dados
        collection = get_collection(interaction.client.db_client, 'welcome_goodbye_configs')
        
        # Converte a cor HEX para inteiro para o preview
        try:
            color = int(welcome_data['welcome_color'].replace('#', ''), 16) if welcome_data['welcome_color'] else discord.Color.blue().value
        except ValueError:
            await interaction.followup.send("❌ A cor HEX é inválida. Por favor, use o formato #FFFFFF.", ephemeral=True)
            return
        
        # Cria um embed de preview
        preview_embed = discord.Embed(
            title=welcome_data['welcome_title'] if welcome_data['welcome_title'] else "Título de Boas-vindas",
            description=welcome_data['welcome_description'] if welcome_data['welcome_description'] else "Olá, {user}! Bem-vindo(a) ao servidor.",
            color=color
        )
        if welcome_data['welcome_image_url']:
            preview_embed.set_image(url=welcome_data['welcome_image_url'])
        if welcome_data['welcome_footer']:
            preview_embed.set_footer(text=welcome_data['welcome_footer'])

        # Envia a mensagem de sucesso e o preview
        await interaction.followup.send("✅ Configurações de boas-vindas salvas com sucesso!", ephemeral=True)
        await interaction.followup.send(embed=preview_embed, ephemeral=True)

        await collection.update_one(
            {'guild_id': guild_id},
            {'$set': {
                'welcome_channel_id': channel_id,
                'welcome_data': welcome_data
            }},
            upsert=True
        )

class GoodbyeModal(Modal, title="Configurar Mensagem de Despedida"):
    
    goodbye_channel = TextInput(
        label="Canal da Mensagem (ID do Canal)",
        placeholder="ID do canal onde a mensagem será enviada",
        required=True,
        max_length=20
    )
    
    goodbye_title = TextInput(
        label="Título do Embed",
        placeholder="Alguém saiu!",
        required=False,
        max_length=256
    )

    goodbye_description = TextInput(
        label="Descrição do Embed",
        placeholder="Adeus, {user}! Sentiremos a sua falta.",
        style=TextStyle.paragraph,
        required=False,
        max_length=4000
    )

    goodbye_footer = TextInput(
        label="Rodapé do Embed",
        placeholder="Desenvolvido por [Seu Bot]",
        required=False,
        max_length=2048
    )

    goodbye_extras = TextInput(
        label="Cor (HEX) e Imagem (URL)",
        placeholder="Exemplo: #FF0000 | https://sua-imagem.com/imagem.png",
        required=False,
        max_length=2048
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id
        
        # Coleta os dados do modal
        try:
            channel_id = int(self.goodbye_channel.value)
        except ValueError:
            await interaction.followup.send("❌ O ID do canal deve ser um número válido.", ephemeral=True)
            return

        goodbye_data = {
            'goodbye_title': self.goodbye_title.value,
            'goodbye_description': self.goodbye_description.value,
            'goodbye_footer': self.goodbye_footer.value
        }

        # Analisa o campo 'goodbye_extras'
        extras = [part.strip() for part in self.goodbye_extras.value.split('|')]
        goodbye_data['goodbye_color'] = extras[0] if len(extras) > 0 and extras[0].startswith('#') else None
        goodbye_data['goodbye_image_url'] = extras[1] if len(extras) > 1 and extras[1].startswith('http') else None

        # Armazena os dados no banco de dados
        collection = get_collection(interaction.client.db_client, 'welcome_goodbye_configs')
        
        # Converte a cor HEX para inteiro para o preview
        try:
            color = int(goodbye_data['goodbye_color'].replace('#', ''), 16) if goodbye_data['goodbye_color'] else discord.Color.red().value
        except ValueError:
            await interaction.followup.send("❌ A cor HEX é inválida. Por favor, use o formato #FFFFFF.", ephemeral=True)
            return
        
        # Cria um embed de preview
        preview_embed = discord.Embed(
            title=goodbye_data['goodbye_title'] if goodbye_data['goodbye_title'] else "Título de Despedida",
            description=goodbye_data['goodbye_description'] if goodbye_data['goodbye_description'] else "Até mais, {user}! Esperamos vê-lo de novo.",
            color=color
        )
        if goodbye_data['goodbye_image_url']:
            preview_embed.set_image(url=goodbye_data['goodbye_image_url'])
        if goodbye_data['goodbye_footer']:
            preview_embed.set_footer(text=goodbye_data['goodbye_footer'])

        # Envia a mensagem de sucesso e o preview
        await interaction.followup.send("✅ Configurações de despedida salvas com sucesso!", ephemeral=True)
        await interaction.followup.send(embed=preview_embed, ephemeral=True)

        await collection.update_one(
            {'guild_id': guild_id},
            {'$set': {
                'goodbye_channel_id': channel_id,
                'goodbye_data': goodbye_data
            }},
            upsert=True
        )

# -----------------
# CLASSES DOS BOTÕES E VIEW
# -----------------
class WelcomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Configurar Boas-vindas", style=discord.ButtonStyle.green, custom_id="config_welcome_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeModal())

class GoodbyeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Configurar Despedidas", style=discord.ButtonStyle.red, custom_id="config_goodbye_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GoodbyeModal())

class ConfigPanelView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(WelcomeButton())
        self.add_item(GoodbyeButton())

# -----------------
# CLASSE PRINCIPAL (COG) E EVENTOS
# -----------------
class WelcomeGoodbyeModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name="painel_boasvindas", description="Cria um painel para configurar as mensagens de entrada e saída.")
    @app_commands.default_permissions(manage_channels=True)
    async def create_config_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Painel de Configuração",
            description="Use os botões abaixo para configurar as mensagens de boas-vindas e despedidas do servidor.",
            color=discord.Color.blue()
        )
        view = ConfigPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config_collection = get_collection(self.bot.db_client, 'welcome_goodbye_configs')
        guild_config = await config_collection.find_one({'guild_id': member.guild.id})

        if not guild_config or not guild_config.get('welcome_channel_id'):
            return

        welcome_channel_id = guild_config['welcome_channel_id']
        channel = discord.utils.get(member.guild.text_channels, id=welcome_channel_id)

        if not channel:
            return

        welcome_data = guild_config.get('welcome_data', {})
        personalized_message = welcome_data.get('personalized_message', '').replace('{user}', member.mention)

        embed = discord.Embed(
            title=welcome_data.get('welcome_title', 'Boas-vindas!'),
            description=welcome_data.get('welcome_description', 'Bem-vindo(a) ao servidor!').replace('{user}', member.mention),
            color=int(welcome_data.get('welcome_color', '#000000').replace('#', ''), 16) if welcome_data.get('welcome_color') else discord.Color.blue().value
        )
        
        if welcome_data.get('use_user_image') == 'sim':
            embed.set_thumbnail(url=member.avatar.url)
        elif welcome_data.get('welcome_image_url'):
            embed.set_image(url=welcome_data.get('welcome_image_url'))

        if welcome_data.get('welcome_footer'):
            embed.set_footer(text=welcome_data.get('welcome_footer'))

        try:
            await channel.send(content=personalized_message, embed=embed)
        except Forbidden:
            print(f"Erro: Sem permissão para enviar mensagem no canal {channel.name} no servidor {member.guild.name}.")


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config_collection = get_collection(self.bot.db_client, 'welcome_goodbye_configs')
        guild_config = await config_collection.find_one({'guild_id': member.guild.id})

        if not guild_config or not guild_config.get('goodbye_channel_id'):
            return

        goodbye_channel_id = guild_config['goodbye_channel_id']
        channel = discord.utils.get(member.guild.text_channels, id=goodbye_channel_id)

        if not channel:
            return
        
        goodbye_data = guild_config.get('goodbye_data', {})
        personalized_message = goodbye_data.get('personalized_message', '').replace('{user}', member.name)

        embed = discord.Embed(
            title=goodbye_data.get('goodbye_title', 'Adeus!'),
            description=goodbye_data.get('goodbye_description', f'{member.name} saiu do servidor.').replace('{user}', member.name),
            color=int(goodbye_data.get('goodbye_color', '#000000').replace('#', ''), 16) if goodbye_data.get('goodbye_color') else discord.Color.red().value
        )

        if goodbye_data.get('use_user_image') == 'sim':
            embed.set_thumbnail(url=member.display_avatar.url)
        elif goodbye_data.get('goodbye_image_url'):
            embed.set_image(url=goodbye_data.get('goodbye_image_url'))

        if goodbye_data.get('goodbye_footer'):
            embed.set_footer(text=goodbye_data.get('goodbye_footer'))

        try:
            await channel.send(content=personalized_message, embed=embed)
        except Forbidden:
            print(f"Erro: Sem permissão para enviar mensagem no canal {channel.name} no servidor {member.guild.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeGoodbyeModule(bot))
    bot.add_view(ConfigPanelView(bot))
