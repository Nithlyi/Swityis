import discord
from discord import app_commands
from utils.embed_creator import EmbedModal, AddDetailsModal

# Define a classe da view (o painel com botões)
class EmbedPanel(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None) # Timeout=None faz a view ser persistente
        self.bot = bot

    @discord.ui.button(label="Criar Novo Embed", style=discord.ButtonStyle.primary, emoji="➕")
    async def create_embed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Abre o modal para criar um novo embed."""
        await interaction.response.send_modal(EmbedModal())

    @discord.ui.button(label="Editar Conteúdo Principal", style=discord.ButtonStyle.secondary, emoji="📝")
    async def edit_embed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pede o ID da mensagem e abre o modal para editar o embed."""
        await interaction.response.send_message(
            "Por favor, **responda a esta mensagem com o ID da mensagem** que contém o embed que você quer editar.",
            ephemeral=True
        )
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            # Espera a resposta do usuário com o ID da mensagem
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            message_id = int(msg.content)
            await msg.delete() # Deleta a mensagem do usuário para limpar o chat

            target_message = await interaction.channel.fetch_message(message_id)
            if target_message.author.id != self.bot.user.id or not target_message.embeds:
                await interaction.followup.send("Não consegui editar a mensagem especificada. Verifique se o ID está correto e se o embed foi criado por mim.", ephemeral=True)
                return
            
            await interaction.followup.send_modal(EmbedModal(initial_embed=target_message.embeds[0], message_to_edit=target_message))

        except ValueError:
            await interaction.followup.send("O ID da mensagem deve ser um número válido.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Tempo esgotado ou ocorreu um erro.", ephemeral=True)

    @discord.ui.button(label="Editar Campos/Rodapé", style=discord.ButtonStyle.secondary, emoji="📋")
    async def edit_details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pede o ID da mensagem e abre o modal para editar os detalhes do embed."""
        await interaction.response.send_message(
            "Por favor, **responda a esta mensagem com o ID da mensagem** que contém o embed que você quer editar os detalhes.",
            ephemeral=True
        )
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            message_id = int(msg.content)
            await msg.delete()

            target_message = await interaction.channel.fetch_message(message_id)
            if target_message.author.id != self.bot.user.id or not target_message.embeds:
                await interaction.followup.send("Não consegui editar a mensagem especificada. Verifique se o ID está correto e se o embed foi criado por mim.", ephemeral=True)
                return
            
            await interaction.followup.send_modal(AddDetailsModal(message_to_edit=target_message))

        except ValueError:
            await interaction.followup.send("O ID da mensagem deve ser um número válido.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Tempo esgotado ou ocorreu um erro.", ephemeral=True)

    @discord.ui.button(label="Deletar Painel", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_panel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deleta a mensagem do painel de embed."""
        await interaction.message.delete()
        await interaction.response.send_message("Painel de embed deletado.", ephemeral=True)

def setup(tree: app_commands.CommandTree, bot: discord.Client):
    """Seta o comando slash para enviar o painel."""
    
    @tree.command(name="embed-panel", description="Envia um painel com botões para criar e editar embeds.")
    @app_commands.default_permissions(administrator=True) # Apenas administradores podem usar
    async def embed_panel_command(interaction: discord.Interaction):
        embed = discord.Embed(
            title="Painel de Criação/Edição de Embeds",
            description="Use os botões abaixo para gerenciar seus embeds. Para editar, você precisará fornecer o ID da mensagem do embed que deseja modificar.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=EmbedPanel(bot))