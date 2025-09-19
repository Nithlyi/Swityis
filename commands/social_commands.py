import discord
from discord.ext import commands
from discord import app_commands, ui
import random
import asyncio



class RetributionView(ui.View):
    def __init__(self, bot, command_name, target_user, original_user):
        super().__init__(timeout=600)
        self.bot = bot
        self.command_name = command_name
        self.target_user = target_user
        self.original_user = original_user

        verb_map = {
            "beijo": "Retribuir Beijo",
            "abraço": "Retribuir Abraço",
            "cafune": "Retribuir Cafuné"
        }
        
        button_label = verb_map.get(command_name, "Retribuir")

        self.retribution_button = ui.Button(
            label=button_label,
            style=discord.ButtonStyle.secondary
        )
        self.retribution_button.callback = self.on_retribute
        self.add_item(self.retribution_button)

    async def on_retribute(self, interaction: discord.Interaction):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("Apenas o usuário que recebeu a ação pode retribuir.", ephemeral=True)
            return

        await interaction.response.defer()

        collection = self.bot.db_client.giveaway_database.social_images
        
        image_data_cursor = collection.aggregate([
            { "$match": { "command": self.command_name } },
            { "$sample": { "size": 1 } }
        ])
        
        image_data = None
        async for doc in image_data_cursor:
            image_data = doc
            break

        if not image_data:
            await interaction.followup.send(f"Não há imagens registradas para o comando {self.command_name}!", ephemeral=True)
            return
        
        title_map = {
            "beijo": f"💋 {self.target_user.display_name} retribuiu o beijo de {self.original_user.display_name}!",
            "abraço": f"🤗 {self.target_user.display_name} retribuiu o abraço de {self.original_user.display_name}!",
            "cafune": f"🥹 {self.target_user.display_name} retribuiu o cafuné de {self.original_user.display_name}!"
        }
        
        description_map = {
            "beijo": f"Eles são tão fofos! 🥺",
            "abraço": f"Amor de sobra! 🥰",
            "cafune": f"Um gesto de carinho de volta! 😊"
        }

        embed = discord.Embed(
            title=title_map.get(self.command_name),
            description=description_map.get(self.command_name),
            color=discord.Color.dark_theme()
        )
        embed.set_image(url=image_data['url'])
        
        embed.set_author(name=self.target_user.display_name, icon_url=self.target_user.avatar.url if self.target_user.avatar else self.target_user.default_avatar.url)
        embed.set_thumbnail(url=self.original_user.avatar.url if self.original_user.avatar else self.original_user.default_avatar.url)
        
        embed.set_footer(text=f"ID da imagem: {image_data['id']}")

        await interaction.followup.send(embed=embed)
        self.stop()

# Adicione a variável owner_id aqui para ser usada na função de setup
def setup(tree: app_commands.CommandTree, bot: commands.Bot, owner_id):
    
    collection = bot.db_client.giveaway_database.social_images

    # Usamos uma função anônima para verificar se o usuário é o dono
    async def is_owner_check(interaction: discord.Interaction) -> bool:
        return interaction.user.id == owner_id

    @tree.command(name="add_social_image", description="Adiciona uma nova imagem a um comando social.")
    @app_commands.describe(
        comando="O comando para adicionar a imagem.",
        imagem_url="O link da imagem/gif."
    )
    @app_commands.choices(
        comando=[
            app_commands.Choice(name="beijo", value="beijo"),
            app_commands.Choice(name="abraço", value="abraço"),
            app_commands.Choice(name="cafune", value="cafune"),
        ]
    )
    @app_commands.check(is_owner_check)
    async def add_social_image(interaction: discord.Interaction, comando: app_commands.Choice[str], imagem_url: str):
        pipeline = [
            { "$match": { "command": comando.value } },
            { "$group": { "_id": None, "max_id": { "$max": "$id" } } }
        ]
        
        results = await collection.aggregate(pipeline).to_list(1)
        max_id = results[0].get("max_id", 0) if results else 0
        next_id = max_id + 1
        
        image_data = {
            "id": next_id,
            "url": imagem_url,
            "command": comando.value
        }
        
        await collection.insert_one(image_data)
        await interaction.response.send_message(f"🖼️ Imagem adicionada com sucesso ao comando **/{comando.value}** com o ID **{next_id}**!", ephemeral=True)

    @tree.command(name="remove_social_image", description="Remove uma imagem de um comando social por ID.")
    @app_commands.describe(
        comando="O comando para remover a imagem.",
        imagem_id="O ID da imagem a ser removida."
    )
    @app_commands.choices(
        comando=[
            app_commands.Choice(name="beijo", value="beijo"),
            app_commands.Choice(name="abraço", value="abraço"),
            app_commands.Choice(name="cafune", value="cafune"),
        ]
    )
    @app_commands.check(is_owner_check)
    async def remove_social_image(interaction: discord.Interaction, comando: app_commands.Choice[str], imagem_id: int):
        result = await collection.delete_one({"command": comando.value, "id": imagem_id})
        
        if result.deleted_count > 0:
            await interaction.response.send_message(f"🗑️ Imagem com ID **{imagem_id}** removida com sucesso do comando **/{comando.value}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Imagem com ID **{imagem_id}** não encontrada para o comando **/{comando.value}**.", ephemeral=True)

    def create_social_command(name, verb, description_text):
        @tree.command(name=name, description=f"✨ {description_text} um usuário.")
        @app_commands.describe(usuario="O usuário para {description_text}.")
        async def social_command(interaction: discord.Interaction, usuario: discord.Member):
            
            collection = bot.db_client.giveaway_database.social_images
            
            image_data_cursor = collection.aggregate([
                { "$match": { "command": name } },
                { "$sample": { "size": 1 } }
            ])
            
            image_data = None
            async for doc in image_data_cursor:
                image_data = doc
                break

            if not image_data:
                await interaction.response.send_message(f"Não há imagens registradas para o comando /{name}! Peça a um moderador para adicionar usando /add_social_image.", ephemeral=True)
                return

            await interaction.response.defer()

            if usuario.id == interaction.user.id:
                title = f"{verb.capitalize()} em si mesmo!"
                desc = f"Parece que {interaction.user.mention} precisa de um pouco de carinho."
            else:
                title = f"{interaction.user.display_name} {verb} {usuario.display_name}!"
                desc = f"{interaction.user.mention} {verb} {usuario.mention} de uma forma muito carinhosa!"

            embed = discord.Embed(
                title=title,
                description=desc,
                color=discord.Color.dark_theme()
            )
            embed.set_image(url=image_data['url'])
            
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            
            embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else usuario.default_avatar.url)
            
            embed.set_footer(text=f"ID da imagem: {image_data['id']}")
            
            view = RetributionView(bot, name, usuario, interaction.user)

            await interaction.followup.send(
                embed=embed,
                view=view
            )

        social_command = commands.cooldown(1, 10, commands.BucketType.user)(social_command)

    #social_command = commands.cooldown(1, 10, commands.BucketType.user)(social_command)

    create_social_command("beijo", "beijou", "beijar")
    create_social_command("abraço", "abraçou", "abraçar")
    create_social_command("cafune", "fez cafuné em", "fazer cafuné em")