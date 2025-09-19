import discord
from discord.ext import commands
from discord import app_commands, ui
from database.database import get_collection
from discord.ui import Modal, TextInput

# -----------------
# CLASSES MODAIS
# -----------------
class AutoroleModal(Modal, title="Configurar Autorole"):
    autorole_id = TextInput(
        label="ID do Cargo",
        placeholder="Digite o ID do cargo a ser atribuído automaticamente",
        required=True,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        guild_id = interaction.guild.id
        
        try:
            role_id = int(self.autorole_id.value)
        except ValueError:
            await interaction.followup.send("❌ O ID do cargo deve ser um número válido.", ephemeral=True)
            return
            
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.followup.send("❌ Cargo não encontrado. Por favor, verifique se o ID está correto.", ephemeral=True)
            return

        collection = get_collection(interaction.client.db_client, 'autorole_configs')
        await collection.update_one(
            {'guild_id': guild_id},
            {'$set': {'role_id': role_id}},
            upsert=True
        )
        
        await interaction.followup.send(f"✅ O cargo {role.name} foi configurado como autorole com sucesso.", ephemeral=True)

# -----------------
# CLASSE PRINCIPAL (COG) E EVENTOS
# -----------------
class AutoroleModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="autorole", description="Configura um cargo que será atribuído automaticamente a novos membros.")
    @app_commands.default_permissions(manage_roles=True)
    async def autorole(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AutoroleModal())

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        collection = get_collection(self.bot.db_client, 'autorole_configs')
        config = await collection.find_one({'guild_id': member.guild.id})
        
        if config and config.get('role_id'):
            role = member.guild.get_role(config['role_id'])
            if role:
                try:
                    await member.add_roles(role)
                    print(f"Cargo {role.name} adicionado a {member.name}.")
                    await asyncio.sleep(0.5)  # Adiciona um delay de 0.5 segundos
                except discord.errors.Forbidden:
                    print(f"Erro: Sem permissão para adicionar o cargo {role.name} a {member.name}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoroleModule(bot))
