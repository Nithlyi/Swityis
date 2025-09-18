import discord
from discord.ext import commands
from discord import app_commands

class AuditLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.logger.info("Módulo AuditLogs carregado.")

    @app_commands.command(name="showlogs", description="Exibe os logs de auditoria recentes (24 horas).")
    @app_commands.default_permissions(administrator=True)
    async def showlogs(self, interaction: discord.Interaction):
        """Comando que exibe os 20 logs de auditoria mais recentes do servidor."""
        await interaction.response.defer(ephemeral=True)

        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("Este comando deve ser usado em um servidor.")
                return

            logs = []
            async for entry in guild.audit_logs(limit=20):
                action = str(entry.action).replace("AuditLogAction.", "")
                user = entry.user
                target = entry.target
                created_at = entry.created_at.strftime("%Y-%m-%d %H:%M:%S")

                log_entry = (
                    f"**Ação:** {action}\n"
                    f"**Usuário:** {user}\n"
                    f"**Alvo:** {target}\n"
                    f"**Data:** {created_at}\n"
                )
                
                # Adiciona detalhes específicos de algumas ações
                if entry.action == discord.AuditLogAction.kick:
                    log_entry += f"**Motivo:** {entry.reason}\n"
                elif entry.action == discord.AuditLogAction.ban:
                    log_entry += f"**Motivo:** {entry.reason}\n"
                elif entry.action == discord.AuditLogAction.member_update:
                    if entry.changes.before.nick != entry.changes.after.nick:
                        log_entry += f"**Mudança:** Apelido de '{entry.changes.before.nick}' para '{entry.changes.after.nick}'\n"
                
                logs.append(log_entry)

            if not logs:
                await interaction.followup.send("Nenhum log de auditoria encontrado nos últimos 20 eventos.")
                return

            embed = discord.Embed(
                title="Logs de Auditoria Recentes (24 horas)",
                description="\n---\n".join(logs),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Exibindo os 20 logs mais recentes. Comandos de auditoria só podem ser usados por administradores.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            self.bot.logger.info(f"Comando /showlogs executado por {interaction.user.name} no servidor {guild.name}.")

        except discord.errors.Forbidden:
            await interaction.followup.send(
                "Erro: O bot não tem permissão para visualizar o log de auditoria. Por favor, conceda a ele a permissão 'View Audit Log'."
            )
        except Exception as e:
            self.bot.logger.error(f"Erro ao executar o comando /showlogs: {e}")
            await interaction.followup.send("Ocorreu um erro ao tentar buscar os logs. Verifique o console para mais detalhes.")