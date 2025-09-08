import discord
from discord import app_commands, ui, Embed
import json
from typing import Optional

# REMOVA ESTA LINHA: from utils.embed_creator import EmbedModal, AddDetailsModal

class EmbedModal(ui.Modal, title='Criador de Embed'):
    def __init__(self, initial_embed: Optional[Embed] = None, message_to_edit: Optional[discord.Message] = None):
        super().__init__()
        
        self.message_to_edit = message_to_edit
        
        self.embed_title = ui.TextInput(
            label='Título do Embed',
            required=False,
            max_length=256,
            default=initial_embed.title if initial_embed and initial_embed.title else None
        )
        self.embed_description = ui.TextInput(
            label='Descrição',
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=4000,
            default=initial_embed.description if initial_embed and initial_embed.description else None
        )
        self.embed_color = ui.TextInput(
            label='Cor (código Hex, ex: #FF5733)',
            required=False,
            max_length=7,
            min_length=7,
            default=f"#{initial_embed.color.value:06X}" if initial_embed and initial_embed.color else None
        )
        self.embed_thumbnail_url = ui.TextInput(
            label='URL da Thumbnail',
            required=False,
            max_length=256,
            default=initial_embed.thumbnail.url if initial_embed and initial_embed.thumbnail else None
        )
        self.embed_image_url = ui.TextInput(
            label='URL da Imagem Principal',
            required=False,
            max_length=256,
            default=initial_embed.image.url if initial_embed and initial_embed.image else None
        )

        self.add_item(self.embed_title)
        self.add_item(self.embed_description)
        self.add_item(self.embed_color)
        self.add_item(self.embed_thumbnail_url)
        self.add_item(self.embed_image_url)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            color_value = None
            if self.embed_color.value:
                color_value = int(self.embed_color.value.replace('#', '0x'), 16)
            
            new_embed = Embed(
                title=self.embed_title.value or None,
                description=self.embed_description.value or None,
                color=color_value
            )
            
            if self.embed_thumbnail_url.value:
                new_embed.set_thumbnail(url=self.embed_thumbnail_url.value)
            
            if self.embed_image_url.value:
                new_embed.set_image(url=self.embed_image_url.value)
            
            if self.message_to_edit:
                for field in self.message_to_edit.embeds[0].fields:
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                if self.message_to_edit.embeds[0].footer:
                    new_embed.set_footer(text=self.message_to_edit.embeds[0].footer.text, icon_url=self.message_to_edit.embeds[0].footer.icon_url)
                if self.message_to_edit.embeds[0].author:
                    new_embed.set_author(name=self.message_to_edit.embeds[0].author.name, icon_url=self.message_to_edit.embeds[0].author.icon_url)

                await self.message_to_edit.edit(embed=new_embed)
                await interaction.response.send_message("Embed editado com sucesso!", ephemeral=True)
            else:
                await interaction.response.send_message(embed=new_embed)
        
        except ValueError:
            await interaction.response.send_message("A cor fornecida não é um código hexadecimal válido. Tente algo como '#FF5733'.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro: {e}", ephemeral=True)


class AddDetailsModal(ui.Modal, title='Adicionar/Editar Campos e Rodapé'):
    def __init__(self, message_to_edit: discord.Message):
        super().__init__()
        
        self.message_to_edit = message_to_edit
        
        existing_embed = message_to_edit.embeds[0]
        fields_text = ""
        if existing_embed.fields:
            fields_text = json.dumps([{"name": f.name, "value": f.value, "inline": f.inline} for f in existing_embed.fields], indent=2)

        self.embed_fields = ui.TextInput(
            label='Campos (JSON)',
            style=discord.TextStyle.paragraph,
            required=False,
            default=fields_text,
            placeholder='[{"name": "nome", "value": "valor", "inline": true}]'
        )
        
        self.embed_footer_text = ui.TextInput(
            label='Texto do Rodapé',
            required=False,
            default=existing_embed.footer.text if existing_embed.footer else None
        )
        
        self.message_content = ui.TextInput(
            label='Mensagem extra',
            required=False,
            max_length=2000
        )
        
        self.add_item(self.embed_fields)
        self.add_item(self.embed_footer_text)
        self.add_item(self.message_content)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed = self.message_to_edit.embeds[0]

            embed.clear_fields()
            if self.embed_fields.value:
                fields_data = json.loads(self.embed_fields.value)
                for field in fields_data:
                    embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))
            
            embed.set_footer(text=self.embed_footer_text.value or Embed.Empty)
            
            await self.message_to_edit.edit(embed=embed)
            
            if self.message_content.value:
                await interaction.channel.send(self.message_content.value)
                
            await interaction.response.send_message("Campos e rodapé atualizados com sucesso!", ephemeral=True)

        except json.JSONDecodeError:
            await interaction.response.send_message("O formato JSON dos campos está inválido. Certifique-se de que é um JSON válido.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro ao editar o embed: {e}", ephemeral=True)

def setup(tree: app_commands.CommandTree):
    @tree.command(name="embed-create", description="Cria um embed com um formulário pop-up.")
    async def create_embed_command(interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())

    @tree.command(name="embed-edit", description="Edita o conteúdo principal de um embed existente do bot.")
    @app_commands.describe(message_id="O ID da mensagem com o embed a ser editado.")
    async def edit_embed_command(interaction: discord.Interaction, message_id: str):
        try:
            target_message = await interaction.channel.fetch_message(int(message_id))
            
            if target_message.author.id != interaction.client.user.id or not target_message.embeds:
                await interaction.response.send_message("Não consegui editar a mensagem especificada. Verifique se o ID está correto e se o embed foi criado por mim.", ephemeral=True)
                return
            
            await interaction.response.send_modal(EmbedModal(initial_embed=target_message.embeds[0], message_to_edit=target_message))
        
        except discord.NotFound:
            await interaction.response.send_message("Mensagem não encontrada. Verifique se o ID está correto.", ephemeral=True)
        except (ValueError, discord.Forbidden):
            await interaction.response.send_message("O ID da mensagem é inválido ou não tenho permissão para acessar.", ephemeral=True)

    @tree.command(name="embed-edit-details", description="Adiciona ou edita campos, rodapé e texto a um embed existente.")
    @app_commands.describe(message_id="O ID da mensagem com o embed a ser editado.")
    async def edit_embed_details_command(interaction: discord.Interaction, message_id: str):
        try:
            target_message = await interaction.channel.fetch_message(int(message_id))
            
            if target_message.author.id != interaction.client.user.id or not target_message.embeds:
                await interaction.response.send_message("Não consegui editar a mensagem especificada. Verifique se o ID está correto e se o embed foi criado por mim.", ephemeral=True)
                return

            await interaction.response.send_modal(AddDetailsModal(message_to_edit=target_message))
        
        except discord.NotFound:
            await interaction.response.send_message("Mensagem não encontrada. Verifique se o ID está correto.", ephemeral=True)
        except (ValueError, discord.Forbidden):
            await interaction.response.send_message("O ID da mensagem é inválido ou não tenho permissão para acessar.", ephemeral=True)