import discord
from discord import app_commands

def setup(tree: app_commands.CommandTree, config: dict, db_client):
    """Seta os comandos de moderação e o comando para definir o cargo."""
    
    # Acessa a coleção de configurações no seu banco de dados
    settings_collection = db_client.seu_banco.settings_collection
    
    # Função para buscar o ID do cargo de moderador no banco de dados
    async def get_mod_role_id():
        settings = await settings_collection.find_one({"_id": "roles"})
        if settings:
            return settings.get("mod_role_id")
        return None

    # Comando para definir o cargo de moderador
    @tree.command(name="setmodrole", description="Define o cargo de moderador para comandos de moderação.")
    @app_commands.describe(cargo="O cargo que terá permissão para moderação.")
    @app_commands.checks.has_permissions(administrator=True) # Só admins podem usar este comando
    async def set_mod_role(interaction: discord.Interaction, cargo: discord.Role):
        await settings_collection.update_one(
            {"_id": "roles"},
            {"$set": {"mod_role_id": cargo.id}},
            upsert=True # Cria o documento se ele não existir
        )
        await interaction.response.send_message(f"Cargo de moderador definido para **{cargo.name}**.", ephemeral=True)

    # Comando de kick, que agora verifica a permissão pelo banco de dados
    @tree.command(name="kick", description="Expulsa um membro do servidor.")
    @app_commands.describe(membro="O membro a ser expulso.")
    async def kick_member(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Nenhum motivo fornecido."):
        mod_role_id = await get_mod_role_id()
        if mod_role_id and mod_role_id in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(f"O membro **{membro.name}** foi expulso. Motivo: {motivo}", ephemeral=True)
            # await membro.kick(reason=motivo)
        else:
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)

    # Adicione mais comandos de moderação aqui, usando a mesma lógica de verificação