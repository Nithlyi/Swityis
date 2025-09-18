import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
import asyncio

class HelpView(discord.ui.View):
    def __init__(self, bot, help_data):
        super().__init__(timeout=180)
        self.bot = bot
        self.help_data = help_data
        self.category_names = list(self.help_data.keys())
        self.current_category = self.category_names[0] if self.category_names else None
        self.current_page = 0
        self.commands_per_page = 5
        self.add_category_buttons()

    def add_category_buttons(self):
        for category in self.category_names:
            button = discord.ui.Button(label=category, style=discord.ButtonStyle.primary, custom_id=f"help_{category}")
            button.callback = self.on_category_button_click
            self.add_item(button)

    async def on_category_button_click(self, interaction: discord.Interaction):
        self.current_category = interaction.data['custom_id'].replace("help_", "")
        self.current_page = 0
        embed = self.create_help_embed(interaction.client.user.avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

    def create_help_embed(self, thumbnail_url):
        commands_list = self.help_data.get(self.current_category, [])
        total_commands = len(commands_list)
        total_pages = (total_commands + self.commands_per_page - 1) // self.commands_per_page
        
        start_index = self.current_page * self.commands_per_page
        end_index = start_index + self.commands_per_page
        
        page_commands = commands_list[start_index:end_index]
        
        embed = discord.Embed(
            title=f"Comandos • {self.current_category}",
            description="Use os botões para navegar entre as categorias e as páginas.",
            color=discord.Color.dark_theme()
        )
        
        if page_commands:
            commands_text = "\n".join([f"`/{cmd['command_name']}`: {cmd['description']}" for cmd in page_commands])
            embed.add_field(name="Comandos", value=commands_text, inline=False)
        else:
            embed.add_field(name="Comandos", value="Nenhum comando nesta categoria.", inline=False)

        embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text=f"Página {self.current_page + 1}/{total_pages if total_pages > 0 else 1}")

        self.update_page_buttons(total_pages)
        return embed

    def update_page_buttons(self, total_pages):
        for item in self.children:
            if item.custom_id in ["prev_page", "next_page"]:
                self.remove_item(item)
        
        if self.current_page > 0:
            prev_button = discord.ui.Button(label="Anterior", style=discord.ButtonStyle.secondary, custom_id="prev_page")
            prev_button.callback = self.on_prev_page_click
            self.add_item(prev_button)

        if self.current_page < total_pages - 1:
            next_button = discord.ui.Button(label="Próximo", style=discord.ButtonStyle.secondary, custom_id="next_page")
            next_button.callback = self.on_next_page_click
            self.add_item(next_button)

    async def on_prev_page_click(self, interaction: discord.Interaction):
        self.current_page -= 1
        embed = self.create_help_embed(interaction.client.user.avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_next_page_click(self, interaction: discord.Interaction):
        self.current_page += 1
        embed = self.create_help_embed(interaction.client.user.avatar.url)
        await interaction.response.edit_message(embed=embed, view=self)


class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_data = {}
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self._load_help_data_from_db()
        
    async def _load_help_data_from_db(self):
        self.help_data = {}
        collection = self.bot.db_client.giveaway_database.help_commands
        
        async for doc in collection.find():
            category = doc.get('category')
            if category not in self.help_data:
                self.help_data[category] = []
            self.help_data[category].append(doc)

    @app_commands.command(name="help", description="Exibe o menu de ajuda do bot.")
    async def help_command(self, interaction: discord.Interaction):
        if not self.help_data:
            await self._load_help_data_from_db()
        
        if not self.help_data:
            await interaction.response.send_message("❌ O menu de ajuda está vazio. O dono do bot precisa adicionar comandos.", ephemeral=True)
            return

        view = HelpView(self.bot, self.help_data)
        embed = view.create_help_embed(self.bot.user.avatar.url)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="add_help_entry", description="[DONO] Adiciona/move um comando para o menu de ajuda.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(category="A categoria do comando.", command_name="O nome do comando (ex: ban).", description="A descrição do comando.")
    async def add_help_entry(self, interaction: discord.Interaction, category: str, command_name: str, description: str):
        collection = self.bot.db_client.giveaway_database.help_commands
        
        # Garante que o nome do comando seja salvo sem barras extras
        command_name = command_name.lstrip('/')

        # Remove todas as entradas existentes com este nome
        result = await collection.delete_many({"command_name": command_name})
        
        # Insere a nova entrada com a categoria e descrição corretas
        await collection.insert_one({
            "category": category,
            "command_name": command_name,
            "description": description
        })
        
        if result.deleted_count > 0:
            message = f"✅ Comando `{command_name}` foi movido para a categoria `{category}`."
        else:
            message = f"✅ Comando `{command_name}` adicionado com sucesso à categoria `{category}`."
        
        await self._load_help_data_from_db()
        
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="sincronizar_ajuda", description="[DONO] Sincroniza todos os comandos com o menu de ajuda.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    async def sync_help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        collection = self.bot.db_client.giveaway_database.help_commands
        
        all_commands = []
        for cmd in self.bot.tree.get_commands():
            all_commands.append({"command_name": cmd.name, "description": cmd.description})
        
        for cmd in self.bot.commands:
            all_commands.append({"command_name": cmd.name, "description": cmd.help or "Sem descrição."})

        added_count = 0
        skipped_count = 0
        
        for cmd_data in all_commands:
            command_name = cmd_data['command_name']
            description = cmd_data['description'] or "Sem descrição."
            
            category = "Diversos"
            if "moderacao" in description.lower() or "mod" in description.lower() or "quarentena" in description.lower():
                category = "Moderação"
            elif "seguranca" in description.lower() or "nuke" in description.lower():
                category = "Segurança"
            elif "clear" in command_name or "ban" in command_name or "kick" in command_name:
                category = "Moderação"
            
            existing_cmd = await collection.find_one({"command_name": command_name})
            
            if not existing_cmd:
                await collection.insert_one({
                    "category": category,
                    "command_name": command_name,
                    "description": description
                })
                added_count += 1
            else:
                skipped_count += 1
                
        await self._load_help_data_from_db()

        await interaction.followup.send(f"✅ Sincronização concluída!\n"
                                        f"• {added_count} novos comandos foram adicionados.\n"
                                        f"• {skipped_count} comandos já estavam no menu.")

    @app_commands.command(name="remover_categoria_ajuda", description="[DONO] Remove uma categoria e todos os seus comandos.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(category="A categoria que deseja remover.")
    async def remove_help_category(self, interaction: discord.Interaction, category: str):
        await interaction.response.defer(ephemeral=True)

        collection = self.bot.db_client.giveaway_database.help_commands
        
        if category not in self.help_data:
            await interaction.followup.send(f"❌ A categoria `{category}` não existe no menu de ajuda.")
            return

        result = await collection.delete_many({"category": category})
        
        if result.deleted_count > 0:
            await self._load_help_data_from_db()
            await interaction.followup.send(f"✅ A categoria `{category}` e {result.deleted_count} comandos foram removidos com sucesso.")
        else:
            await interaction.followup.send(f"❌ Não foi possível encontrar comandos na categoria `{category}`.")
            
    @app_commands.command(name="limpar_categoria_ajuda", description="[DONO] Limpa comandos duplicados de outras categorias.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(category="A categoria principal a ser mantida.")
    async def clean_help_category(self, interaction: discord.Interaction, category: str):
        await interaction.response.defer(ephemeral=True)

        collection = self.bot.db_client.giveaway_database.help_commands

        if category not in self.help_data:
            await interaction.followup.send(f"❌ A categoria `{category}` não existe no menu de ajuda. Nada a ser limpo.")
            return

        commands_to_keep = [doc['command_name'] for doc in self.help_data[category]]
        
        removed_count = 0
        for other_category in self.help_data:
            if other_category != category:
                for command_name in commands_to_keep:
                    result = await collection.delete_many(
                        {"category": other_category, "command_name": command_name}
                    )
                    removed_count += result.deleted_count
        
        await self._load_help_data_from_db()
        await interaction.followup.send(f"✅ Limpeza concluída! Foram removidos {removed_count} comandos duplicados de outras categorias.")

    @app_commands.command(name="mover_comandos", description="[DONO] Move todos os comandos de uma categoria para outra.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(categoria_origem="A categoria de onde os comandos serão movidos.", categoria_destino="A categoria para onde os comandos serão enviados.")
    async def move_commands(self, interaction: discord.Interaction, categoria_origem: str, categoria_destino: str):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands

        result = await collection.update_many(
            {"category": categoria_origem},
            {"$set": {"category": categoria_destino}}
        )

        await self._load_help_data_from_db()
        await interaction.followup.send(f"✅ {result.modified_count} comandos foram movidos da categoria `{categoria_origem}` para `{categoria_destino}`.")

    @app_commands.command(name="mover_comando", description="[DONO] Move um comando específico para uma nova categoria.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(nome_comando="O nome do comando a ser movido.", nova_categoria="A nova categoria do comando.")
    async def move_specific_command(self, interaction: discord.Interaction, nome_comando: str, nova_categoria: str):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands
        
        nome_comando = nome_comando.lstrip('/')

        result = await collection.update_one(
            {"command_name": nome_comando},
            {"$set": {"category": nova_categoria}}
        )

        if result.modified_count > 0:
            await self._load_help_data_from_db()
            await interaction.followup.send(f"✅ Comando `{nome_comando}` movido com sucesso para a categoria `{nova_categoria}`.")
        else:
            await interaction.followup.send(f"❌ Não foi possível encontrar o comando `{nome_comando}` no banco de dados.")

    @app_commands.command(name="reorganizar_ajuda", description="[DONO] Reorganiza automaticamente todos os comandos com base em palavras-chave.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    async def reorganize_help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands

        updated_count = 0
        
        async for doc in collection.find():
            command_name = doc['command_name']
            description = doc.get('description', 'Sem descrição.')
            current_category = doc['category']

            new_category = "Diversos"
            
            if "moderacao" in description.lower() or "mod" in description.lower() or "quarentena" in description.lower():
                new_category = "Moderação"
            elif "seguranca" in description.lower() or "nuke" in description.lower():
                new_category = "Segurança"
            elif "clear" in command_name or "ban" in command_name or "kick" in command_name:
                new_category = "Moderação"
            
            if new_category != current_category:
                await collection.update_one(
                    {"_id": doc['_id']},
                    {"$set": {"category": new_category}}
                )
                updated_count += 1
        
        await self._load_help_data_from_db()
        
        await interaction.followup.send(f"✅ Reorganização concluída! {updated_count} comandos foram movidos para a categoria correta.")

    @app_commands.command(name="corrigir_barras", description="[DONO] Remove barras extras do nome dos comandos no banco de dados.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    async def fix_slashes(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands

        corrected_count = 0
        
        async for doc in collection.find({"command_name": {"$regex": r"^\/+"}}):
            old_name = doc['command_name']
            new_name = old_name.lstrip('/')
            
            if old_name != new_name:
                await collection.update_one(
                    {"_id": doc['_id']},
                    {"$set": {"command_name": new_name}}
                )
                corrected_count += 1
        
        await self._load_help_data_from_db()
        
        await interaction.followup.send(f"✅ Correção concluída! Foram removidas barras extras de {corrected_count} comandos no banco de dados.")
    
    @app_commands.command(name="remover_comando", description="[DONO] Remove um comando do menu de ajuda.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    @app_commands.describe(nome_comando="O nome do comando a ser removido (ex: ban).")
    async def remove_command_entry(self, interaction: discord.Interaction, nome_comando: str):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands

        # Remove barras extras para garantir que a busca funcione
        nome_comando = nome_comando.lstrip('/')
        
        # Remove a entrada com o nome do comando especificado
        result = await collection.delete_one({"command_name": nome_comando})
        
        if result.deleted_count > 0:
            await self._load_help_data_from_db()
            await interaction.followup.send(f"✅ Comando `{nome_comando}` removido com sucesso do menu de ajuda.")
        else:
            await interaction.followup.send(f"❌ Não foi possível encontrar o comando `{nome_comando}` no menu de ajuda.")

    # NOVO COMANDO PARA CONSERTAR TUDO
    @app_commands.command(name="consertar_ajuda_geral", description="[DONO] Limpa comandos duplicados e remove barras extras.")
    @app_commands.check(lambda interaction: str(interaction.user.id) == interaction.client.config.get('owner_id'))
    async def fix_all_help_entries(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        collection = self.bot.db_client.giveaway_database.help_commands

        # 1. Obter todos os documentos e limpar as barras extras
        cleaned_docs = {}
        async for doc in collection.find():
            cmd_name = doc['command_name'].lstrip('/')
            
            # Se o comando já existe, é um duplicado, então ignoramos
            if cmd_name not in cleaned_docs:
                doc['command_name'] = cmd_name
                cleaned_docs[cmd_name] = doc
        
        # 2. Excluir todos os documentos do banco de dados
        await collection.delete_many({})
        
        # 3. Inserir apenas os documentos limpos e únicos
        if cleaned_docs:
            await collection.insert_many(list(cleaned_docs.values()))
        
        # 4. Recarregar o cache
        await self._load_help_data_from_db()
        
        await interaction.followup.send(f"✅ Limpeza geral concluída! O menu de ajuda foi reorganizado, removendo duplicatas e barras extras.")

def setup(bot):
    bot.add_cog(HelpCommand(bot))
    print("Módulo de ajuda carregado.")