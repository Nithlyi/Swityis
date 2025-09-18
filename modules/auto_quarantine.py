import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import re
import asyncio

class AutoQuarantine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Substitua "Nome do seu Cargo" pelo nome exato do seu cargo de quarentena.
        self.quarantine_role_name = "Quarentena" 
        # Substitua 000000000000000000 pelo ID do canal de quarentena.
        self.quarantine_channel_id = 000000000000000000 
        self.risk_threshold = 50 # Pontos necessários para ativar a quarentena
        self.quarantine_duration_hours = 24 # Duração da quarentena em horas

    def calculate_risk_score(self, member: discord.Member) -> int:
        """Calcula a pontuação de risco de um membro com base em critérios de segurança."""
        score = 0
        now = discord.utils.utcnow()
        account_age = now - member.created_at

        # Critério 1: Idade da conta
        if account_age <= datetime.timedelta(days=2):
            score += 50
        elif account_age <= datetime.timedelta(days=7):
            score += 20
        
        # Critério 2: Falta de avatar
        if not member.avatar:
            score += 30

        # Critério 3: Nome de usuário suspeito
        if re.search(r'[^a-zA-Z\s]{5,}', member.name) or re.match(r'\d+', member.name):
            score += 25
        if len(member.name) <= 2:
            score += 15

        return score

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        
        if member.bot:
            return

        risk_score = self.calculate_risk_score(member)
        
        if risk_score >= self.risk_threshold:
            self.bot.logger.info(f"Membro {member.name} (ID: {member.id}) com pontuação de risco de {risk_score} (pontuação limite: {self.risk_threshold}).")

            quarantine_role = discord.utils.get(member.guild.roles, name=self.quarantine_role_name)
            
            if not quarantine_role:
                self.bot.logger.error(f"Cargo de quarentena '{self.quarantine_role_name}' não encontrado.")
                return

            try:
                await member.add_roles(quarantine_role, reason=f"Quarentena automática: pontuação de risco {risk_score}.")
                
                quarantine_collection = self.bot.db_client.giveaway_database.quarantined_users
                await quarantine_collection.insert_one({
                    "user_id": member.id,
                    "quarantined_at": datetime.datetime.utcnow(),
                    "guild_id": member.guild.id
                })
                
                quarantine_channel = member.guild.get_channel(self.quarantine_channel_id)
                if quarantine_channel:
                    await quarantine_channel.send(f"🚨 Alerta de Segurança: O membro {member.mention} foi colocado em quarentena automaticamente por ser uma conta suspeita (pontuação de risco: **{risk_score}**). A quarentena durará **{self.quarantine_duration_hours} horas**.")

                self.bot.logger.info(f"Membro {member.name} (ID: {member.id}) colocado em quarentena automaticamente por {self.quarantine_duration_hours} horas.")
                
            except discord.Forbidden:
                self.bot.logger.error("O bot não tem permissão para adicionar o cargo de quarentena.")
            except Exception as e:
                self.bot.logger.error(f"Erro ao colocar membro em quarentena: {e}")

    @tasks.loop(minutes=1)
    async def check_quarantine_expiry(self):
        """Verifica e remove a quarentena de membros cujo tempo expirou."""
        quarantine_collection = self.bot.db_client.giveaway_database.quarantined_users
        
        # Pega a data de agora menos a duração da quarentena
        expiry_time = datetime.datetime.utcnow() - datetime.timedelta(hours=self.quarantine_duration_hours)
        
        # Pega todos os usuários que estão em quarentena por mais tempo que o permitido
        async for quarantined_user_data in quarantine_collection.find({"quarantined_at": {"$lte": expiry_time}}):
            guild = self.bot.get_guild(quarantined_user_data["guild_id"])
            if not guild:
                await quarantine_collection.delete_one({"_id": quarantined_user_data["_id"]})
                continue
            
            member = guild.get_member(quarantined_user_data["user_id"])
            quarantine_role = discord.utils.get(guild.roles, name=self.quarantine_role_name)
            
            if member and quarantine_role:
                try:
                    await member.remove_roles(quarantine_role, reason="Quarentena automática expirada.")
                    self.bot.logger.info(f"Quarentena de {member.display_name} (ID: {member.id}) expirou e foi removida.")
                except discord.Forbidden:
                    self.bot.logger.warning(f"Não foi possível remover o cargo de quarentena de {member.display_name}. Verifique as permissões.")
                except Exception as e:
                    self.bot.logger.error(f"Erro ao remover quarentena de {member.display_name}: {e}")
            
            # Remove o registro do banco de dados
            await quarantine_collection.delete_one({"_id": quarantined_user_data["_id"]})

    @commands.Cog.listener()
    async def on_ready(self):
        # Inicia a tarefa de verificação quando o bot está pronto
        self.check_quarantine_expiry.start()

    def cog_unload(self):
        # Para a tarefa quando o cog é descarregado
        self.check_quarantine_expiry.cancel()
    
    # --- NOVO COMANDO ---
    @app_commands.command(name="remova_quarentena", description="Remove a quarentena de um membro.")
    @app_commands.describe(membro="O membro para remover da quarentena.")
    @app_commands.default_permissions(manage_roles=True)
    async def remove_quarantine(self, interaction: discord.Interaction, membro: discord.Member):
        quarantine_role = discord.utils.get(interaction.guild.roles, name=self.quarantine_role_name)
        
        if not quarantine_role:
            await interaction.response.send_message(f"❌ O cargo de quarentena '{self.quarantine_role_name}' não foi encontrado. Por favor, configure-o.", ephemeral=True)
            return

        # Verifica se o membro tem o cargo de quarentena
        if quarantine_role not in membro.roles:
            await interaction.response.send_message(f"❌ O membro {membro.mention} não está em quarentena.", ephemeral=True)
            return

        try:
            await membro.remove_roles(quarantine_role, reason=f"Quarentena removida manualmente por {interaction.user.display_name}.")
            
            # Remove o registro do banco de dados
            quarantine_collection = self.bot.db_client.giveaway_database.quarantined_users
            await quarantine_collection.delete_one({"user_id": membro.id, "guild_id": interaction.guild.id})
            
            await interaction.response.send_message(f"✅ Quarentena de {membro.mention} removida com sucesso.", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para remover o cargo de quarentena. Verifique as permissões do bot.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ocorreu um erro ao remover a quarentena: {e}", ephemeral=True)

def setup(bot):
    bot.add_cog(AutoQuarantine(bot))
    print("Módulo de Quarentena Automática (com duração) carregado.")