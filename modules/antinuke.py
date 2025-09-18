import discord
from discord.ext import commands
import asyncio
import collections

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Um dicionário para rastrear ações de moderação por usuário
        # Ex: {user_id: [timestamp1, timestamp2, ...]}
        self.mod_actions = collections.defaultdict(list)

        # Configurações do Anti-Nuke
        self.threshold = 5  # Número de ações antes de reagir
        self.time_frame = 10  # Tempo em segundos para a detecção (10 segundos)

    async def check_for_nuke(self, user: discord.Member, action: str):
        """Verifica se um usuário está realizando uma ação de "nuke"."""
        now = discord.utils.utcnow()
        self.mod_actions[user.id].append(now)

        # Remove timestamps antigos (fora do tempo de detecção)
        self.mod_actions[user.id] = [t for t in self.mod_actions[user.id] if (now - t).total_seconds() <= self.time_frame]

        if len(self.mod_actions[user.id]) >= self.threshold:
            self.bot.logger.warning(f"Atenção! Possível ataque de 'nuke' detectado por {user.display_name} (ID: {user.id})! Ação: {action}")
            
            # Limpa o histórico de ações para este usuário para evitar múltiplas punições
            self.mod_actions[user.id].clear()

            # Evita punir o dono do bot
            if user.id == self.bot.config.get('owner_id'):
                self.bot.logger.info("O dono do bot está realizando ações suspeitas, ignorando a punição.")
                return

            # Ação de proteção: remove todos os cargos do usuário e o expulsa do servidor
            try:
                # Remove todos os cargos do usuário
                for role in user.roles:
                    try:
                        await user.remove_roles(role)
                    except discord.Forbidden:
                        self.bot.logger.warning(f"Não foi possível remover o cargo {role.name} de {user.display_name} por falta de permissões.")

                # Kika o usuário
                await user.kick(reason=f"Ativou o sistema Anti-Nuke: {self.threshold} ações de moderação em {self.time_frame} segundos.")
                self.bot.logger.info(f"O usuário {user.display_name} foi kickado por ativar o Anti-Nuke.")
            except discord.Forbidden:
                self.bot.logger.error("O bot não tem permissão para kikar o usuário. Ajuste as permissões do bot!")
            except Exception as e:
                self.bot.logger.error(f"Ocorreu um erro ao tentar punir o usuário: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Monitora a exclusão de canais."""
        # Se o canal foi deletado pelo bot, ignoramos
        audit_logs = channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete)
        async for entry in audit_logs:
            if entry.user.bot:
                return
            await self.check_for_nuke(entry.user, "deletar canal")
            break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Monitora a exclusão de cargos."""
        audit_logs = role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete)
        async for entry in audit_logs:
            if entry.user.bot:
                return
            await self.check_for_nuke(entry.user, "deletar cargo")
            break

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Monitora o banimento de membros."""
        audit_logs = guild.audit_logs(limit=1, action=discord.AuditLogAction.ban)
        async for entry in audit_logs:
            if entry.user.bot:
                return
            await self.check_for_nuke(entry.user, "banir membro")
            break

def setup(bot: commands.Bot):
    bot.logger.info("Módulo AntiNuke carregado.")
    bot.add_cog(AntiNuke(bot))