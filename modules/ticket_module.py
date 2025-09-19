import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
from database.database import get_collection
from bson import ObjectId
import asyncio
import os
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

class TicketButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.bot))

class TicketModal(ui.Modal, title="Abrir Ticket"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    subject = ui.TextInput(
        label="Assunto do Ticket",
        placeholder="Descreva o motivo do seu contato...",
        required=True,
        min_length=5,
        max_length=100
    )

    description = ui.TextInput(
        label="Descrição Detalhada",
        placeholder="Forneça mais detalhes sobre o seu problema...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild_id = interaction.guild_id
        collection = get_collection(self.bot.db_client, f"tickets_{guild_id}")
        
        channel_name = f"ticket-{interaction.user.name.lower().replace(' ', '-')}"
        
        ticket_category = discord.utils.get(interaction.guild.categories, name="Tickets")
        if not ticket_category:
            ticket_category = await interaction.guild.create_category("Tickets")

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await handle_rate_limit(interaction.guild.create_text_channel,
            name=channel_name,
            category=ticket_category,
            overwrites=overwrites
        )

        # A CORREÇÃO ESTÁ AQUI:
        # Monta a descrição em uma variável para quebra de linha
        embed_description = f"Ticket aberto por {interaction.user.mention} (ID: {interaction.user.id}).\n\n**Assunto:** {self.subject.value}"
        
        # Adiciona a descrição detalhada com quebra de linha
        if self.description.value:
            embed_description += f"\n**Descrição:**\n{self.description.value}"
        else:
            embed_description += "\n**Descrição:** Nenhuma"
            
        ticket_embed = discord.Embed(
            title=f"Novo Ticket de Suporte",
            description=embed_description,
            color=discord.Color.blue()
        )

        ticket_embed.set_footer(text=f"Ticket ID: {interaction.user.id}")

        view = TicketView(self.bot)
        initial_message = await handle_rate_limit(ticket_channel.send, embed=ticket_embed, view=view)
        
        await collection.insert_one({
            "channel_id": ticket_channel.id,
            "user_id": interaction.user.id,
            "guild_id": guild_id,
            "created_at": datetime.datetime.now(),
            "subject": self.subject.value,
            "initial_message_id": initial_message.id
        })

        await interaction.followup.send(f"Seu ticket foi criado em {ticket_channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("Este botão só pode ser usado em um canal de ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript = f"Transcrição do Ticket\nTicket ID: {interaction.channel.id}\nUsuário: {interaction.channel.topic}\nData: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        async for message in interaction.channel.history(limit=100, oldest_first=True):
            transcript += f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {message.content}\n"

        file_name = f"ticket_{interaction.channel.id}_transcript.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(transcript)

        ticket_owner = interaction.guild.get_member(int(interaction.channel.topic)) if interaction.channel.topic else None
        
        try:
            if ticket_owner:
                await handle_rate_limit(ticket_owner.send, f"Aqui está a transcrição do seu ticket no servidor {interaction.guild.name}:", file=discord.File(file_name))
        except discord.Forbidden:
            pass
        
        await interaction.channel.delete()
        os.remove(file_name)

class PanelTicketView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketButton(self.bot))

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal(self.bot))

class TicketModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_id = self.bot.user.id
        self.panel_collection = get_collection(self.bot.db_client, "ticket_panels")
        
    async def get_panel_data(self, guild_id: int):
        data = await self.panel_collection.find_one({"guild_id": guild_id})
        return data

    @app_commands.command(name="painel_ticket", description="Cria um painel de tickets personalizável.")
    @app_commands.default_permissions(manage_channels=True)
    async def panel_ticket(self, interaction: discord.Interaction):
        class PanelModal(ui.Modal, title="Personalizar Painel de Ticket"):
            def __init__(self, bot, panel_collection):
                super().__init__()
                self.bot = bot
                self.panel_collection = panel_collection
                
                self.panel_title = ui.TextInput(label="Título do Embed", required=False, max_length=256)
                self.panel_description = ui.TextInput(label="Descrição do Embed", required=False, max_length=4000)
                self.panel_footer = ui.TextInput(label="Rodapé do Embed", required=False, max_length=2048)
                self.image_url = ui.TextInput(label="URL da Imagem", required=False, max_length=2048)
                self.color_hex = ui.TextInput(label="Cor do Embed (HEX)", placeholder="#FFFFFF", required=False, min_length=7, max_length=7)
                
                self.add_item(self.panel_title)
                self.add_item(self.panel_description)
                self.add_item(self.panel_footer)
                self.add_item(self.image_url)
                self.add_item(self.color_hex)
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    color_value = int(self.color_hex.value.replace("#", "0x"), 16) if self.color_hex.value else 0x3498DB
                except ValueError:
                    await modal_interaction.response.send_message("Cor HEX inválida. Por favor, insira um valor como #FFFFFF.", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title=self.panel_title.value or "Suporte ao Cliente",
                    description=self.panel_description.value or "Clique no botão abaixo para abrir um ticket.",
                    color=discord.Color(color_value)
                )
                if self.panel_footer.value:
                    embed.set_footer(text=self.panel_footer.value)
                if self.image_url.value:
                    embed.set_image(url=self.image_url.value)
                    
                view = PanelTicketView(self.bot)
                
                await modal_interaction.response.defer(ephemeral=True)

                message = await modal_interaction.followup.send(embed=embed, view=view, ephemeral=False)
                
                panel_data = {
                    "guild_id": modal_interaction.guild_id,
                    "channel_id": modal_interaction.channel_id,
                    "message_id": message.id,
                    "title": self.panel_title.value,
                    "description": self.panel_description.value,
                    "footer": self.panel_footer.value,
                    "image_url": self.image_url.value,
                    "color_hex": self.color_hex.value
                }

                try:
                    await self.panel_collection.update_one(
                        {"guild_id": modal_interaction.guild_id},
                        {"$set": panel_data},
                        upsert=True
                    )
                except Exception as e:
                    print(f"Erro ao salvar o painel no MongoDB: {e}")

        await interaction.response.send_modal(PanelModal(self.bot, self.panel_collection))

    @app_commands.command(name="fechar_ticket", description="Fecha o ticket atual.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def close_ticket(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("Este comando só pode ser usado em um canal de ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript = f"Transcrição do Ticket\nTicket ID: {interaction.channel.id}\nUsuário: {interaction.channel.topic}\nData: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        async for message in interaction.channel.history(limit=None, oldest_first=True):
            transcript += f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {message.content}\n"

        file_name = f"ticket_{interaction.channel.id}_transcript.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(transcript)

        ticket_owner = interaction.guild.get_member(int(interaction.channel.topic)) if interaction.channel.topic else None
        
        try:
            if ticket_owner:
                await ticket_owner.send(f"Aqui está a transcrição do seu ticket no servidor {interaction.guild.name}:", file=discord.File(file_name))
        except discord.Forbidden:
            pass
        
        await interaction.channel.delete()
        os.remove(file_name)

    @app_commands.command(name="editar_ticket", description="Edita a mensagem inicial de um ticket.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def edit_ticket(self, interaction: discord.Interaction, novo_texto: str):
        if not interaction.channel.name.startswith("ticket-"):
            await interaction.response.send_message("Este comando só pode ser usado em um canal de ticket.", ephemeral=True)
            return

        ticket_collection = get_collection(self.bot.db_client, f"tickets_{interaction.guild_id}")
        ticket_data = await ticket_collection.find_one({"channel_id": interaction.channel_id})

        if not ticket_data or not ticket_data.get("initial_message_id"):
            await interaction.response.send_message("Não foi possível encontrar a mensagem inicial deste ticket.", ephemeral=True)
            return
            
        try:
            initial_message = await interaction.channel.fetch_message(ticket_data.get("initial_message_id"))
            
            embed = initial_message.embeds[0]
            embed.description = novo_texto
            
            await initial_message.edit(embed=embed)
            await interaction.response.send_message("Mensagem inicial do ticket editada com sucesso!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("Mensagem inicial não encontrada.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketModule(bot))
    
    # Carrega a View do botão de fechar para todos os tickets
    bot.add_view(TicketView(bot))
    
    # Carrega os painéis de tickets salvos no banco de dados e os recria
    collection = get_collection(bot.db_client, "ticket_panels")
    async for panel_data in collection.find():
        try:
            channel = bot.get_channel(panel_data["channel_id"])
            if channel:
                try:
                    await channel.fetch_message(panel_data["message_id"])
                    # Adiciona a view do painel para que seja persistente
                    panel_view = PanelTicketView(bot)
                    bot.add_view(panel_view)
                except discord.NotFound:
                    embed = discord.Embed(
                        title=panel_data.get("title", "Suporte ao Cliente"),
                        description=panel_data.get("description", "Clique no botão abaixo para abrir um ticket."),
                        color=discord.Color(int(panel_data.get("color_hex", "#3498DB").replace("#", "0x"), 16))
                    )
                    if panel_data.get("footer"):
                        embed.set_footer(text=panel_data["footer"])
                    if panel_data.get("image_url"):
                        embed.set_image(url=panel_data["image_url"])
                    
                    panel_view = PanelTicketView(bot)
                    message = await channel.send(embed=embed, view=panel_view)
                    
                    await collection.update_one(
                        {"guild_id": panel_data["guild_id"]},
                        {"$set": {"message_id": message.id}}
                    )
        except Exception as e:
            print(f"Erro ao carregar o painel de ticket da guilda {panel_data.get('guild_id')}: {e}")