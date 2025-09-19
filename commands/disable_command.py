import discord
from discord import app_commands
from discord.ext import commands
import os

class DisableCommand(commands.Cog):
    def __init__(self, bot: commands.Bot, owner_id: int):
        self.bot = bot
        self.owner_id = owner_id
        self.disabled_commands = []
        self.original_commands = {}
        
    def is_owner(self, interaction: discord.Interaction):
        return interaction.user.id == self.owner_id

    @app_commands.command(name="disable", description="Desativa um comando do bot. Apenas o dono pode usar.")
    @app_commands.describe(command_name="O nome do comando para desativar.")
    async def disable(self, interaction: discord.Interaction, command_name: str):
        if not self.is_owner(interaction):
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        command = self.bot.tree.get_command(command_name)
        if command and command.name not in self.disabled_commands:
            # Responde à interação de forma diferida para ganhar tempo.
            await interaction.response.defer(ephemeral=True)
            
            # Armazena o comando original
            self.original_commands[command.name] = command
            # Remove o comando da árvore para desativá-lo
            self.bot.tree.remove_command(command.name)
            self.disabled_commands.append(command.name)
            await self.bot.tree.sync()
            
            # Envia a mensagem de sucesso como um "follow-up".
            await interaction.followup.send(f"Comando `{command_name}` desativado com sucesso.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Comando `{command_name}` não encontrado ou já está desativado.", ephemeral=True)
    
    @commands.cooldown(1, 60, commands.BucketType.user)  # Cooldown de 60 segundos por usuário
    @app_commands.command(name="enable", description="Reativa um comando do bot. Apenas o dono pode usar.")
    @app_commands.describe(command_name="O nome do comando para reativar.")
    async def enable(self, interaction: discord.Interaction, command_name: str):
        if not self.is_owner(interaction):
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if command_name in self.disabled_commands:
            # Responde à interação de forma diferida para ganhar tempo.
            await interaction.response.defer(ephemeral=True)
            
            original_command = self.original_commands.get(command_name)
            if original_command:
                # Adiciona o comando de volta à árvore
                self.bot.tree.add_command(original_command)
                self.disabled_commands.remove(command_name)
                del self.original_commands[command_name]
                await self.bot.tree.sync()
                
                # Envia a mensagem de sucesso como um "follow-up".
                await interaction.followup.send(f"Comando `{command_name}` reativado com sucesso.", ephemeral=True)
            else:
                await interaction.followup.send(f"Não foi possível reativar o comando `{command_name}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Comando `{command_name}` não encontrado na lista de desativados.", ephemeral=True)

    @enable.error
    async def enable_error(self, interaction: discord.Interaction, error):
        if isinstance(error, commands.CommandOnCooldown):
            await interaction.response.send_message(f"Este comando está em cooldown. Tente novamente em {error.retry_after:.1f} segundos.", ephemeral=True)
        else:
            raise error

async def setup(bot: commands.Bot, owner_id: int):
    await bot.add_cog(DisableCommand(bot, owner_id))