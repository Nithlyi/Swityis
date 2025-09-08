import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from discord.utils import get
import logging
from typing import Optional, Union
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticCollection
import asyncio

# Configuração de logging para este módulo
logger = logging.getLogger(__name__)

# --- Checks personalizados ---
def is_bot_owner():
    """Verifica se o usuário que executou o comando é o proprietário do bot."""
    async def predicate(interaction: discord.Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(predicate)

# --- Funções de Ajuda ---
async def get_or_create_profile(collection: AgnosticCollection, user_id: int):
    """Obtém o perfil do usuário ou cria um novo se não existir."""
    profile = await collection.find_one({"user_id": user_id})
    if not profile:
        profile = {
            "user_id": user_id,
            "profile_description": None,
            "profile_color": "#2f3136",
            "active_banner_id": None,
            "active_border_id": None,
            "currency": 0,
            "xp": 0
        }
        await collection.insert_one(profile)
    return profile

async def get_profile_embed(member: discord.Member, profiles: AgnosticCollection, shop: AgnosticCollection):
    """Cria o embed do perfil com base nos dados do usuário."""
    profile_data = await get_or_create_profile(profiles, member.id)
    
    color_hex = profile_data.get('profile_color', "#2f3136")
    try:
        color = discord.Color.from_str(color_hex)
    except ValueError:
        color = discord.Color.from_str("#2f3136") # Cor padrão se a hex for inválida
        
    banner_url = None
    if profile_data.get('active_banner_id'):
        banner_item = await shop.find_one({"item_id": profile_data['active_banner_id']})
        if banner_item and 'item_url' in banner_item:
            banner_url = banner_item['item_url']

    embed = discord.Embed(
        title=f"Perfil de {member.display_name}",
        description=profile_data.get('profile_description', "Nenhuma descrição definida."),
        color=color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Moedas", value=f"🪙 {profile_data.get('currency', 0)}", inline=True)
    embed.add_field(name="XP", value=f"✨ {profile_data.get('xp', 0)}", inline=True)
    
    if banner_url:
        embed.set_image(url=banner_url)
    
    return embed

async def _use_item(interaction: discord.Interaction, item_id: int, profiles: AgnosticCollection, inventory: AgnosticCollection, shop: AgnosticCollection):
    """Lógica unificada para usar um item do inventário."""
    inventory_item = await inventory.find_one({"user_id": interaction.user.id, "item_id": item_id})
    if not inventory_item:
        await interaction.followup.send("Você não possui este item em seu inventário.", ephemeral=True)
        return
        
    shop_item = await shop.find_one({"item_id": item_id})
    if not shop_item:
        await interaction.followup.send("Erro: Item não encontrado na loja.", ephemeral=True)
        return
    
    item_type = shop_item['item_type']
    
    column_to_update = None
    if item_type == "banner":
        column_to_update = "active_banner_id"
    elif item_type == "border":
        column_to_update = "active_border_id"
    
    if not column_to_update:
        await interaction.followup.send("Tipo de item inválido.", ephemeral=True)
        return

    await profiles.update_one(
        {"user_id": interaction.user.id},
        {"$set": {column_to_update: item_id}}
    )
    
    embed = discord.Embed(
        title="Item Ativado!",
        description=f"Você ativou o item **{shop_item['item_name']}**.",
        color=discord.Color.green()
    )
    if 'item_url' in shop_item and shop_item['item_url']:
        embed.set_thumbnail(url=shop_item['item_url'])
        
    await interaction.followup.send(embed=embed, ephemeral=True)
    logger.info(f"Usuário {interaction.user.id} ativou o item {item_id} ({item_type}).")


# --- Views Interativas ---
class ProfileView(View):
    def __init__(self, bot, member, shop_collection, inventory_collection):
        super().__init__(timeout=None)
        self.bot = bot
        self.member = member
        self.shop_collection = shop_collection
        self.inventory_collection = inventory_collection

    @discord.ui.button(label="Ver Inventário", style=discord.ButtonStyle.secondary)
    async def view_inventory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        inventory_items_cursor = self.inventory_collection.find({"user_id": interaction.user.id})
        inventory_item_ids = [item['item_id'] for item in await inventory_items_cursor.to_list(length=None)]
        
        shop_items_cursor = self.shop_collection.find({"item_id": {"$in": inventory_item_ids}})
        shop_items = await shop_items_cursor.to_list(length=None)
        
        if not shop_items:
            await interaction.followup.send("Seu inventário está vazio.", ephemeral=False)
            return

        view = InventoryView(shop_items, interaction.user.id, self.shop_collection, self.inventory_collection, self.bot.get_cog("Personalization").profiles_collection)
        embed = view.get_inventory_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    @discord.ui.button(label="Ir para a Loja", style=discord.ButtonStyle.secondary)
    async def go_to_shop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        await interaction.followup.send("Indo para a loja!", ephemeral=False)
        await interaction.client.get_command("loja")(interaction) # Chama o comando da loja

class ShopView(View):
    def __init__(self, shop_items, author_id, profiles_collection, inventory_collection, shop_collection):
        super().__init__(timeout=300)
        self.shop_items = shop_items
        self.items_per_page = 5
        self.current_page = 0
        self.total_pages = (len(self.shop_items) + self.items_per_page - 1) // self.items_per_page
        self.author_id = author_id
        self.profiles_collection = profiles_collection
        self.inventory_collection = inventory_collection
        self.shop_collection = shop_collection
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        previous_button = Button(label="Anterior", style=discord.ButtonStyle.secondary, custom_id="previous_page", disabled=(self.current_page == 0))
        previous_button.callback = self.previous_page
        
        next_button = Button(label="Próximo", style=discord.ButtonStyle.secondary, custom_id="next_page", disabled=(self.current_page >= self.total_pages - 1))
        next_button.callback = self.next_page
        
        buy_button = Button(label="Comprar Item", style=discord.ButtonStyle.success, custom_id="buy_item")
        buy_button.callback = self.buy_item

        self.add_item(previous_button)
        self.add_item(next_button)
        self.add_item(buy_button)

    def get_shop_embed(self):
        embed = discord.Embed(
            title="✨ Loja do Servidor ✨",
            description="Compre itens para personalizar seu perfil!",
            color=discord.Color.gold()
        )
        
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        items_on_page = self.shop_items[start_index:end_index]

        if items_on_page and 'item_url' in items_on_page[0]:
            embed.set_image(url=items_on_page[0]['item_url'])
        
        for item in items_on_page:
            embed.add_field(
                name=f"ID: {item['item_id']} | {item['item_name']}",
                value=f"Tipo: `{item['item_type'].capitalize()}`\nPreço: 🪙 {item['item_price']}",
                inline=False
            )
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.total_pages}")
        return embed

    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Essa navegação é para a pessoa que usou o comando.", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_shop_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Essa navegação é para a pessoa que usou o comando.", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_shop_embed(), view=self)
    
    async def buy_item(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Esse comando é para a pessoa que usou o comando.", ephemeral=True)
            return
        await interaction.response.send_modal(BuyModal(self.profiles_collection, self.inventory_collection, self.shop_collection))

class BuyModal(discord.ui.Modal, title="Comprar Item"):
    def __init__(self, profiles: AgnosticCollection, inventory: AgnosticCollection, shop: AgnosticCollection):
        super().__init__()
        self.profiles_collection = profiles
        self.inventory_collection = inventory
        self.shop_collection = shop
    
    item_id = discord.ui.TextInput(label="ID do Item", placeholder="Digite o ID do item que deseja comprar.")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_id = int(self.item_id.value)
        except ValueError:
            await interaction.response.send_message("ID do item inválido. Por favor, digite um número.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        profile = await get_or_create_profile(self.profiles_collection, interaction.user.id)
        item = await self.shop_collection.find_one({"item_id": item_id})
        
        if not item:
            await interaction.followup.send("Item não encontrado na loja.", ephemeral=True)
            return

        profile_currency = profile.get('currency', 0)
        
        if profile_currency < item['item_price']:
            await interaction.followup.send("Você não tem moedas suficientes para comprar este item.", ephemeral=True)
            return
            
        inventory_item = await self.inventory_collection.find_one({"user_id": interaction.user.id, "item_id": item_id})
        if inventory_item:
            await interaction.followup.send("Você já possui este item.", ephemeral=True)
            return

        new_currency = profile_currency - item['item_price']
        
        await self.profiles_collection.update_one(
            {"user_id": interaction.user.id},
            {"$set": {"currency": new_currency}}
        )
        await self.inventory_collection.insert_one({
            "user_id": interaction.user.id,
            "item_id": item_id
        })

        await interaction.followup.send(f"Parabéns! Você comprou **{item['item_name']}** por 🪙 {item['item_price']}. Suas moedas restantes: 🪙 {new_currency}", ephemeral=True)
        logger.info(f"Usuário {interaction.user.id} comprou o item {item['item_name']} (ID: {item_id}).")

class InventoryView(View):
    def __init__(self, items, author_id, shop_collection, inventory_collection, profiles_collection):
        super().__init__(timeout=300)
        self.items = items
        self.items_per_page = 6
        self.current_page = 0
        self.total_pages = (len(self.items) + self.items_per_page - 1) // self.items_per_page
        self.author_id = author_id
        self.shop_collection = shop_collection
        self.inventory_collection = inventory_collection
        self.profiles_collection = profiles_collection
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        previous_button = Button(label="Anterior", style=discord.ButtonStyle.secondary, disabled=(self.current_page == 0))
        previous_button.callback = self.previous_page
        
        next_button = Button(label="Próximo", style=discord.ButtonStyle.secondary, disabled=(self.current_page >= self.total_pages - 1))
        next_button.callback = self.next_page
        
        use_button = Button(label="Usar Item", style=discord.ButtonStyle.success)
        use_button.callback = self.use_item_from_inventory

        self.add_item(previous_button)
        self.add_item(next_button)
        self.add_item(use_button)

    def get_inventory_embed(self):
        embed = discord.Embed(
            title="Seu Inventário",
            description="Seus itens adquiridos. Use o ID para equipar um item.",
            color=discord.Color.blue()
        )
        
        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page
        items_on_page = self.items[start_index:end_index]
        
        for item in items_on_page:
            item_url = item.get('item_url', '')
            embed.add_field(
                name=f"ID: {item['item_id']} | {item['item_name']}",
                value=f"Tipo: `{item['item_type'].capitalize()}`\n[Miniatura]({item_url})",
                inline=True
            )
            
        embed.set_footer(text=f"Página {self.current_page + 1}/{self.total_pages}")
        return embed

    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Essa navegação é para a pessoa que usou o comando.", ephemeral=True)
            return

        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_inventory_embed(), view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Essa navegação é para a pessoa que usou o comando.", ephemeral=True)
            return

        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_inventory_embed(), view=self)
    
    async def use_item_from_inventory(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UseModal(self.profiles_collection, self.inventory_collection, self.shop_collection))

class UseModal(discord.ui.Modal, title="Usar Item"):
    def __init__(self, profiles: AgnosticCollection, inventory: AgnosticCollection, shop: AgnosticCollection):
        super().__init__()
        self.profiles_collection = profiles
        self.inventory_collection = inventory
        self.shop_collection = shop
    
    item_id = discord.ui.TextInput(label="ID do Item", placeholder="Digite o ID do item que deseja usar.")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_id = int(self.item_id.value)
        except ValueError:
            await interaction.response.send_message("ID do item inválido. Por favor, digite um número.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        await _use_item(interaction, item_id, self.profiles_collection, self.inventory_collection, self.shop_collection)

class Personalization(commands.Cog):
    def __init__(self, bot: commands.Bot, db_client: AsyncIOMotorClient):
        self.bot = bot
        self.db = db_client.mydatabase
        self.profiles_collection = self.db.profiles
        self.shop_collection = self.db.shop_items
        self.inventory_collection = self.db.user_inventory

        # Cria os índices do banco de dados para otimização
        asyncio.create_task(self.setup_db_indexes())

    async def setup_db_indexes(self):
        """Cria índices para otimização de consultas nas coleções."""
        try:
            await self.profiles_collection.create_index([("user_id", 1)], unique=True)
            await self.shop_collection.create_index([("item_id", 1)], unique=True)
            await self.inventory_collection.create_index([("user_id", 1), ("item_id", 1)], unique=True)
            logger.info("Índices do MongoDB para personalização criados com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao criar índices do MongoDB: {e}", exc_info=True)

    @app_commands.command(name="perfil", description="Veja seu perfil personalizado ou o de outro usuário.")
    @app_commands.describe(membro="O membro cujo perfil você quer ver (opcional).")
    async def profile_command(self, interaction: discord.Interaction, membro: Optional[discord.Member]):
        await interaction.response.defer(ephemeral=False)
        member = membro or interaction.user
        
        embed = await get_profile_embed(member, self.profiles_collection, self.shop_collection)
        
        view = ProfileView(self.bot, member, self.shop_collection, self.inventory_collection)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="loja", description="Veja os itens disponíveis na loja.")
    async def shop_command(self, interaction: discord.Interaction):
        shop_items_cursor = self.shop_collection.find({})
        shop_items = await shop_items_cursor.to_list(length=None)
        
        if not shop_items:
            await interaction.response.send_message("A loja está vazia no momento.", ephemeral=True)
            return

        view = ShopView(shop_items, interaction.user.id, self.profiles_collection, self.inventory_collection, self.shop_collection)
        embed = view.get_shop_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    @app_commands.command(name="inventario", description="Veja todos os seus itens do inventário.")
    async def inventory_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        inventory_items_cursor = self.inventory_collection.find({"user_id": interaction.user.id})
        inventory_item_ids = [item['item_id'] for item in await inventory_items_cursor.to_list(length=None)]
        
        shop_items_cursor = self.shop_collection.find({"item_id": {"$in": inventory_item_ids}})
        shop_items = await shop_items_cursor.to_list(length=None)
        
        if not shop_items:
            await interaction.followup.send("Seu inventário está vazio.", ephemeral=False)
            return

        view = InventoryView(shop_items, interaction.user.id, self.shop_collection, self.inventory_collection, self.profiles_collection)
        embed = view.get_inventory_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    @app_commands.command(name="usar", description="Usa um item do seu inventário para o seu perfil.")
    @app_commands.describe(item_id="O ID do item que você quer usar.")
    async def use_command(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)
        await _use_item(interaction, item_id, self.profiles_collection, self.inventory_collection, self.shop_collection)

    @app_commands.command(name="adicionar_item", description="Adiciona um novo item à loja (apenas para o proprietário do bot).")
    @app_commands.describe(tipo="Tipo do item ('banner' ou 'border').", nome="Nome do item.", preco="Preço do item.", arquivo="Anexar um arquivo para o banner ou a borda (opcional).", url="URL da imagem do item (opcional).")
    @is_bot_owner()
    async def add_item_to_shop_command(self, interaction: discord.Interaction, tipo: str, nome: str, preco: int, arquivo: Optional[discord.Attachment] = None, url: Optional[str] = None):
        if tipo.lower() not in ["banner", "border"]:
            await interaction.response.send_message("Tipo de item inválido. Use 'banner' ou 'border'.", ephemeral=True)
            return
        
        if preco <= 0:
            await interaction.response.send_message("O preço deve ser um número positivo.", ephemeral=True)
            return
            
        if arquivo and url:
            await interaction.response.send_message("Você não pode enviar um arquivo e uma URL ao mesmo tempo. Escolha apenas um.", ephemeral=True)
            return

        item_url = None
        if arquivo:
            item_url = arquivo.url
        elif url:
            item_url = url
        else:
            await interaction.response.send_message("Você deve fornecer uma URL ou anexar um arquivo para o item.", ephemeral=True)
            return

        last_item = await self.shop_collection.find_one(sort=[("item_id", -1)])
        next_id = (last_item["item_id"] + 1) if last_item and 'item_id' in last_item else 1
        
        try:
            await self.shop_collection.insert_one(
                {
                    "item_id": next_id,
                    "item_name": nome,
                    "item_type": tipo.lower(),
                    "item_url": item_url,
                    "item_price": preco
                }
            )
            await interaction.response.send_message(f"Item **{nome}** (ID: `{next_id}`) adicionado à loja com sucesso! [Visualizar]({item_url})", ephemeral=True)
            logger.info(f"Novo item adicionado à loja: {nome} (ID: {next_id}, Tipo: {tipo}, Preço: {preco}).")
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro ao adicionar o item. Erro: {e}", ephemeral=True)
            logger.error(f"Erro ao adicionar item à loja: {e}", exc_info=True)

    @app_commands.command(name="remover_item", description="Remove um item da loja (apenas para o proprietário do bot).")
    @app_commands.describe(item_id="O ID do item que você quer remover.")
    @is_bot_owner()
    async def remove_item_from_shop_command(self, interaction: discord.Interaction, item_id: int):
        await interaction.response.defer(ephemeral=True)

        item = await self.shop_collection.find_one({"item_id": item_id})
        if not item:
            await interaction.followup.send(f"Item com ID `{item_id}` não encontrado na loja.", ephemeral=True)
            return
        
        try:
            await self.shop_collection.delete_one({"item_id": item_id})
            await interaction.followup.send(f"Item **{item['item_name']}** (ID: `{item_id}`) removido da loja com sucesso.", ephemeral=True)
            logger.info(f"Item removido da loja: {item['item_name']} (ID: {item_id}).")
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao remover o item. Erro: {e}", ephemeral=True)
            logger.error(f"Erro ao remover item da loja: {e}", exc_info=True)

    @app_commands.command(name="setar_moedas", description="Define a quantidade de moedas de um usuário (apenas para o dono do bot).")
    @app_commands.describe(membro="O membro para definir as moedas.", quantidade="A nova quantidade de moedas.")
    @is_bot_owner()
    async def set_currency_command(self, interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        
        await get_or_create_profile(self.profiles_collection, membro.id) # Garante que o perfil existe
        
        await self.profiles_collection.update_one(
            {"user_id": membro.id},
            {"$set": {"currency": quantidade}}
        )
        
        await interaction.followup.send(f"As moedas de {membro.display_name} foram definidas para 🪙 {quantidade}.", ephemeral=True)
        logger.info(f"O proprietário do bot definiu as moedas de {membro.id} para {quantidade}.")

    @app_commands.command(name="setar_xp", description="Define a quantidade de XP de um usuário (apenas para o dono do bot).")
    @app_commands.describe(membro="O membro para definir o XP.", quantidade="A nova quantidade de XP.")
    @is_bot_owner()
    async def set_xp_command(self, interaction: discord.Interaction, membro: discord.Member, quantidade: int):
        await interaction.response.defer(ephemeral=True)
        
        await get_or_create_profile(self.profiles_collection, membro.id) # Garante que o perfil existe e tenha o campo 'xp'
        
        await self.profiles_collection.update_one(
            {"user_id": membro.id},
            {"$set": {"xp": quantidade}}
        )
        
        await interaction.followup.send(f"O XP de {membro.display_name} foi definido para ✨ {quantidade}.", ephemeral=True)
        logger.info(f"O proprietário do bot definiu o XP de {membro.id} para {quantidade}.")

async def setup_personalization(bot: commands.Bot, db_client: AsyncIOMotorClient):
    """
    Função de setup para registrar os comandos de personalização e configurar as coleções.
    """
    await bot.add_cog(Personalization(bot, db_client))
