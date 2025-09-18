import discord
from discord.ext import commands
from discord import app_commands
from database.database import get_collection
import re

# -----------------
# CLASSES MODAIS
# -----------------
class AntispamModal(discord.ui.Modal, title="Configurar Anti-Spam"):
    limit = discord.ui.TextInput(
        label="Limite de Mensagens (por minuto)",
        placeholder="Digite um número, ex: 5",
        required=True,
        max_length=5
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id
        
        try:
            limit_val = int(self.limit.value)
            if limit_val <= 0:
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ O limite de mensagens deve ser um número inteiro positivo.", ephemeral=True)
            return

        collection = get_collection(interaction.client.db_client, 'antispam_configs')
        await collection.update_one(
            {'guild_id': guild_id},
            {'$set': {'limit': limit_val, 'enabled': True}},
            upsert=True
        )
        
        await interaction.followup.send(f"✅ Limite de anti-spam definido para {limit_val} mensagens por minuto.", ephemeral=True)

class AntilinkModal(discord.ui.Modal, title="Configurar Anti-Link"):
    enabled = discord.ui.TextInput(
        label="Ativar Anti-Link (sim/não)",
        placeholder="Digite 'sim' para ativar",
        required=True,
        min_length=3,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id
        
        enabled_val = self.enabled.value.lower() == 'sim'

        collection = get_collection(interaction.client.db_client, 'antilink_configs')
        await collection.update_one(
            {'guild_id': guild_id},
            {'$set': {'enabled': enabled_val}},
            upsert=True
        )
        
        status = "ativado" if enabled_val else "desativado"
        await interaction.followup.send(f"✅ O sistema anti-link foi {status} com sucesso.", ephemeral=True)

# -----------------
# CLASSE PRINCIPAL (COG) E EVENTOS
# -----------------
class AntiSpamAntilinkModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_cooldowns = {}
        # Expressão regular para encontrar URLs
        self.url_regex = re.compile(r'https?://\S+|www\.\S+|\S+\.\S{2,}')

    @app_commands.command(name="antispam", description="Configura o sistema de anti-spam.")
    @app_commands.default_permissions(manage_messages=True)
    async def antispam(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AntispamModal())

    @app_commands.command(name="antilink", description="Ativa ou desativa o sistema de anti-link.")
    @app_commands.default_permissions(manage_messages=True)
    async def antilink(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AntilinkModal())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Lógica Anti-Link
        antilink_collection = get_collection(self.bot.db_client, 'antilink_configs')
        antilink_config = await antilink_collection.find_one({'guild_id': message.guild.id})
        
        if antilink_config and antilink_config.get('enabled') and self.url_regex.search(message.content):
            try:
                await message.delete()
                await message.channel.send(f"❌ {message.author.mention}, links não são permitidos neste servidor.", delete_after=5)
                return  # Parar a execução para não verificar anti-spam

            except discord.errors.Forbidden:
                print(f"Erro: Sem permissão para excluir mensagens no canal {message.channel.name}.")

        # Lógica Anti-Spam
        antispam_collection = get_collection(self.bot.db_client, 'antispam_configs')
        antispam_config = await antispam_collection.find_one({'guild_id': message.guild.id})

        if antispam_config and antispam_config.get('enabled'):
            user_id = str(message.author.id)
            if user_id not in self.spam_cooldowns:
                self.spam_cooldowns[user_id] = []

            self.spam_cooldowns[user_id].append(message.created_at)
            
            # Remove mensagens antigas da lista
            one_minute_ago = discord.utils.utcnow() - discord.timedelta(minutes=1)
            self.spam_cooldowns[user_id] = [ts for ts in self.spam_cooldowns[user_id] if ts > one_minute_ago]
            
            if len(self.spam_cooldowns[user_id]) > antispam_config['limit']:
                try:
                    await message.channel.send(f"🛑 {message.author.mention}, não faça spam! As suas mensagens serão excluídas.", delete_after=5)
                    # Exclui as mensagens recentes do usuário
                    messages_to_delete = [msg async for msg in message.channel.history(limit=antispam_config['limit'] + 1, before=message.created_at)]
                    await message.channel.delete_messages(messages_to_delete)
                    self.spam_cooldowns[user_id] = [] # Limpa o registro do usuário
                except discord.errors.Forbidden:
                    print(f"Erro: Sem permissão para gerir mensagens no canal {message.channel.name}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiSpamAntilinkModule(bot))
