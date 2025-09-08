import discord
from discord.ext import commands
from discord import app_commands, utils
import time
import math
import random

# A classe Cog é a forma recomendada de estruturar módulos em discord.py
class EconomySystem(commands.Cog):
    def __init__(self, bot, db_client):
        self.bot = bot
        self.db = db_client['your_database_name'] # Substitua pelo nome do seu banco de dados
        self.users_collection = self.db['users'] # Coleção para armazenar os dados dos usuários
        self.xp_cooldown_seconds = 60 # Tempo de espera entre ganhos de XP (em segundos)
        self.level_up_messages = [
            "Parabéns, {user}! Você subiu de nível para **{level}**!",
            "Uau! {user} agora é nível **{level}**! Continue assim!",
            "Novo nível alcançado! {user} é agora nível **{level}**."
        ]

    # Função para calcular o XP necessário para o próximo nível
    def calculate_required_xp(self, level):
        return 5 * (level**2) + 50 * level + 100

    # Função para criar a barra de progresso
    def create_xp_bar(self, current_xp, required_xp, bar_length=15):
        percentage = (current_xp / required_xp)
        filled_blocks = int(percentage * bar_length)
        empty_blocks = bar_length - filled_blocks
        
        # Cria a barra com os blocos preenchidos e vazios
        bar = "█" * filled_blocks + " " * empty_blocks
        
        return f"[{bar}] {int(percentage * 100)}%"

    # Evento disparado quando uma mensagem é enviada
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignora mensagens de bots ou de DMs
        if message.author.bot or not message.guild:
            return

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        # Cria um ID único para o usuário no servidor
        user_data_id = f"{user_id}_{guild_id}"

        # Busca ou cria o documento do usuário
        user_data = await self.users_collection.find_one({'_id': user_data_id})
        
        if not user_data:
            user_data = {
                '_id': user_data_id,
                'user_id': user_id,
                'guild_id': guild_id,
                'xp': 0,
                'level': 1,
                'coins': 0,
                'last_message_time': 0
            }
            await self.users_collection.insert_one(user_data)

        current_time = time.time()
        
        # Verifica o cooldown
        if current_time - user_data['last_message_time'] >= self.xp_cooldown_seconds:
            # Ganho de XP e moedas
            xp_gain = random.randint(15, 25)
            coins_gain = random.randint(1, 5)
            
            user_data['xp'] += xp_gain
            user_data['coins'] += coins_gain
            user_data['last_message_time'] = current_time
            
            # Verifica se o usuário subiu de nível
            required_xp = self.calculate_required_xp(user_data['level'])
            if user_data['xp'] >= required_xp:
                user_data['level'] += 1
                user_data['xp'] -= required_xp
                
                # Envia mensagem de nível
                level_up_message = random.choice(self.level_up_messages)
                await message.channel.send(level_up_message.format(user=message.author.mention, level=user_data['level']))

            await self.users_collection.update_one({'_id': user_data_id}, {'$set': user_data})
        
        # Garante que outros comandos continuem funcionando
        await self.bot.process_commands(message)

    @app_commands.command(name="profile", description="Mostra o seu perfil de level e economia.")
    async def profile_command(self, interaction: discord.Interaction):
        user_data = await self.users_collection.find_one({'_id': f"{interaction.user.id}_{interaction.guild.id}"})

        if not user_data:
            await interaction.response.send_message("Você ainda não tem um perfil. Envie uma mensagem no servidor para começar!", ephemeral=True)
            return

        required_xp = self.calculate_required_xp(user_data['level'])
        
        # Cria a barra de progresso
        xp_bar = self.create_xp_bar(user_data['xp'], required_xp)
        
        embed = discord.Embed(
            title=f"Perfil de {interaction.user.display_name}",
            color=discord.Color.purple()
        )
        
        # Adiciona a imagem de perfil do usuário como thumbnail
        embed.set_thumbnail(url=interaction.user.avatar.url)
        
        embed.add_field(name="Nível", value=f"```fix\n{user_data['level']}\n```", inline=True)
        embed.add_field(name="Moedas", value=f"```yaml\n{user_data['coins']}\n```", inline=True)
        
        embed.description = (
            f"**XP**: `{user_data['xp']}/{required_xp}`\n"
            f"**Progresso**: `{xp_bar}`"
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="topxp", description="Mostra o ranking de usuários por XP.")
    async def topxp_command(self, interaction: discord.Interaction):
        leaderboard = await self.users_collection.find({'guild_id': str(interaction.guild.id)}).sort('xp', -1).limit(10).to_list(10)
        
        if not leaderboard:
            await interaction.response.send_message("Não há dados de ranking neste servidor ainda.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Ranking de XP em {interaction.guild.name}",
            color=discord.Color.gold()
        )
        
        rank_text = ""
        for i, user_data in enumerate(leaderboard):
            member = interaction.guild.get_member(int(user_data['user_id']))
            if member:
                rank_text += f"**{i + 1}.** {member.mention} - Nível **{user_data['level']}**\n"
        
        embed.description = rank_text
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="topcoins", description="Mostra o ranking de usuários por moedas.")
    async def topcoins_command(self, interaction: discord.Interaction):
        leaderboard = await self.users_collection.find({'guild_id': str(interaction.guild.id)}).sort('coins', -1).limit(10).to_list(10)

        if not leaderboard:
            await interaction.response.send_message("Não há dados de ranking neste servidor ainda.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Ranking de Moedas em {interaction.guild.name}",
            color=discord.Color.gold()
        )

        rank_text = ""
        for i, user_data in enumerate(leaderboard):
            member = interaction.guild.get_member(int(user_data['user_id']))
            if member:
                rank_text += f"**{i + 1}.** {member.mention} - {user_data['coins']} moedas\n"

        embed.description = rank_text
        await interaction.response.send_message(embed=embed)
    
async def setup(bot, db_client):
    """Adiciona o cog de economia ao bot."""
    await bot.add_cog(EconomySystem(bot, db_client))