import discord
from discord.ext import commands
from discord import app_commands

def is_owner_check(config):
    """Cria uma verificação que retorna True se o usuário for o dono do bot."""
    async def predicate(interaction: discord.Interaction):
        owner_id = config.get('owner_id')
        if owner_id:
            return interaction.user.id == int(owner_id)
        return False
    return app_commands.check(predicate)

def setup(tree: app_commands.CommandTree, bot: commands.Bot, config: dict):
    @tree.command(name="list-commands", description="Lista todos os comandos slash carregados e sincronizados.")
    @is_owner_check(config)
    async def list_commands(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        commands_list = []
        
        # Pega os comandos globais
        global_commands = tree.get_commands(guild=None)
        if global_commands:
            commands_list.append("## Comandos Globais:")
            for cmd in global_commands:
                commands_list.append(f"- `/{cmd.name}`: {cmd.description}")

        # Pega os comandos do servidor, se houver um ID configurado
        guild_id = config.get('guild_id')
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            guild_commands = tree.get_commands(guild=guild)
            if guild_commands:
                commands_list.append("\n## Comandos do Servidor:")
                for cmd in guild_commands:
                    commands_list.append(f"- `/{cmd.name}`: {cmd.description}")
        
        if not commands_list:
            await interaction.followup.send("Nenhum comando foi encontrado.")
            return
            
        # Nova lógica para dividir a resposta em partes menores
        response_text = ""
        for line in commands_list:
            if len(response_text) + len(line) + 1 > 1900: # 1900 para ter uma margem de segurança
                await interaction.followup.send(response_text)
                response_text = line
            else:
                response_text += "\n" + line
        
        # Envia a última parte da mensagem
        if response_text:
            await interaction.followup.send(response_text)