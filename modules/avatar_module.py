import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime

class DownloadButton(discord.ui.Button):
    def __init__(self, avatar_url: str):
        super().__init__(label="Baixar Avatar", style=discord.ButtonStyle.link, url=avatar_url)

class AvatarModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Mostra o avatar de um membro.")
    async def avatar(self, interaction: discord.Interaction, membro: discord.Member = None):
        member = membro or interaction.user
        
        # Cria um embed com o avatar do membro
        embed = discord.Embed(
            title=f"Avatar de {member.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Solicitado por {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

        # Adiciona a view com o botão de download
        view = discord.ui.View()
        view.add_item(DownloadButton(member.display_avatar.url))

        # Responde à interação com o embed e o botão
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(AvatarModule(bot))
