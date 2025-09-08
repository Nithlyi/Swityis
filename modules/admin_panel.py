import discord
from discord import app_commands

def setup(tree: app_commands.CommandTree, config: dict, db_client):
    """Seta os comandos de administração e o comando para definir o cargo."""
    
    # Acessa a coleção de configurações no seu banco de dados
    settings_collection = db_client.seu_banco.settings_collection
    
    # Função para buscar o ID do cargo de administrador no banco de dados
    async def get_admin_role_id():
        settings = await settings_collection.find_one({"_id": "roles"})
        if settings:
            return settings.get("admin_role_id")
        return None

    # Comando para definir o cargo de administrador
    @tree.command(name="setadminrole", description="Define o cargo de administrador.")
    @app_commands.describe(cargo="O cargo que terá permissão de administrador.")
    @app_commands.checks.has_permissions(administrator=True) # Só admins podem usar este comando
    async def set_admin_role(interaction: discord.Interaction, cargo: discord.Role):
        await settings_collection.update_one(
            {"_id": "roles"},
            {"$set": {"admin_role_id": cargo.id}},
            upsert=True
        )
        await interaction.response.send_message(f"Cargo de administrador definido para **{cargo.name}**.", ephemeral=True)

    # Comando de ban, que agora verifica a permissão pelo banco de dados
    @tree.command(name="ban", description="Bane um membro do servidor.")
    @app_commands.describe(membro="O membro a ser banido.")
    async def ban_member(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Nenhum motivo fornecido."):
        admin_role_id = await get_admin_role_id()
        if admin_role_id and admin_role_id in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(f"O membro **{membro.name}** foi banido. Motivo: {motivo}", ephemeral=True)
            # await membro.ban(reason=motivo)
        else:
            await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)