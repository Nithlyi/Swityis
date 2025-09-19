import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import random
import re
from datetime import datetime, timedelta

def format_time_remaining(end_time):
    """Formata a diferença de tempo em uma string."""
    remaining = end_time - datetime.utcnow()
    if remaining.total_seconds() <= 0:
        return "Tempo esgotado!"

    days, seconds = divmod(remaining.total_seconds(), 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if minutes > 0:
        parts.append(f"{int(minutes)}m")
    if seconds > 0:
        parts.append(f"{int(seconds)}s")

    return " ".join(parts)

# Define a classe da View para os botões do sorteio
class GiveawayView(ui.View):
    def __init__(self, bot, premio: str, end_time: datetime, original_description: str, image_url: str = None, footer_text: str = None):
        super().__init__(timeout=None)
        self.bot = bot
        self.premio = premio
        self.end_time = end_time
        self.original_description = original_description
        self.image_url = image_url
        self.footer_text = footer_text
        self.participants = set()

        # Cria o botão "Participar"
        self.participate_button = ui.Button(
            label="Participar", 
            style=discord.ButtonStyle.danger,
            emoji="🎉",
            custom_id="giveaway_participate"
        )
        self.participate_button.callback = self.on_participate
        self.add_item(self.participate_button)

    async def on_participate(self, interaction: discord.Interaction):
        if interaction.user.bot:
            await interaction.response.send_message("Bots não podem participar do sorteio.", ephemeral=True)
            return

        if datetime.utcnow() >= self.end_time:
            await interaction.response.send_message("O sorteio já terminou!", ephemeral=True)
            return

        if interaction.user.id in self.participants:
            await interaction.response.send_message("Você já está participando deste sorteio!", ephemeral=True)
        else:
            self.participants.add(interaction.user.id)
            await interaction.response.send_message("Você entrou no sorteio!", ephemeral=True)

def setup(tree: app_commands.CommandTree, bot: commands.Bot):

    async def parse_duration(time_str: str):
        """Converte uma string de duração (ex: '1h30m') em segundos."""
        seconds = 0
        if not time_str:
            return 0
        
        time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        pattern = re.compile(r'(\d+)([smhd])')
        
        matches = pattern.findall(time_str)
        if not matches:
            raise ValueError("Formato de duração inválido. Use '1h', '30m', '15s', etc.")
        
        for value, unit in matches:
            seconds += int(value) * time_units[unit]
            
        return seconds

    @tree.command(name="sorteio", description="Inicia um sorteio com opções personalizáveis.")
    @app_commands.describe(
        premio="O prêmio do sorteio.",
        duracao="A duração do sorteio (ex: 1h, 30m, 15s).",
        descricao="A descrição do sorteio (opcional).",
        imagem_url="URL de uma imagem para o sorteio (opcional).",
        rodape="Texto no rodapé do sorteio (opcional)."
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(
        interaction: discord.Interaction,
        premio: str,
        duracao: str,
        descricao: str = None,
        imagem_url: str = None,
        rodape: str = None
    ):
        await interaction.response.defer()

        try:
            duration_seconds = await parse_duration(duracao)
            if duration_seconds <= 0:
                await interaction.followup.send("A duração do sorteio deve ser maior que zero.", ephemeral=True)
                return
        except ValueError as e:
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)
            return

        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        view = GiveawayView(bot, premio, end_time, descricao, imagem_url, rodape)

        embed = discord.Embed(
            title="🎉 Sorteio 🎉",
            description=f"**Prêmio:** {premio}\n" + (descricao if descricao else ""),
            color=discord.Color.gold(),
            timestamp=end_time
        )
        embed.add_field(name="Para participar:", value="Clique no botão 'Participar' abaixo!", inline=False)
        embed.set_footer(text=f"Partipantes: {len(view.participants)} | {rodape if rodape else ''}")

        if imagem_url:
            embed.set_image(url=imagem_url)

        try:
            giveaway_message = await interaction.channel.send(embed=embed, view=view)
        except Exception as e:
            await interaction.followup.send(f"Erro ao iniciar o sorteio: {e}", ephemeral=True)
            return

        await interaction.followup.send("Sorteio iniciado com sucesso!", ephemeral=True)

        # Loop para atualizar o cronômetro
        while datetime.utcnow() < end_time:
            await asyncio.sleep(30)  # Atualiza a cada 30 segundos
            try:
                # Recria o embed para atualizar o cronômetro e a contagem de participantes
                updated_embed = discord.Embed(
                    title="🎉 Sorteio 🎉",
                    description=f"**Prêmio:** {premio}\n" + (descricao if descricao else ""),
                    color=discord.Color.gold(),
                    timestamp=end_time
                )
                updated_embed.add_field(name="Para participar:", value="Clique no botão 'Participar' abaixo!", inline=False)
                updated_embed.add_field(name="⏰ Tempo restante", value=format_time_remaining(end_time), inline=False)
                updated_embed.set_footer(text=f"Partipantes: {len(view.participants)} | {rodape if rodape else ''}")
                if imagem_url:
                    updated_embed.set_image(url=imagem_url)

                await giveaway_message.edit(embed=updated_embed, view=view)
            except discord.NotFound:
                return
            except Exception as e:
                bot.logger.error(f"Erro ao atualizar o sorteio: {e}")

        # Fim do sorteio
        try:
            # Desabilita o botão
            for item in view.children:
                item.disabled = True
            await giveaway_message.edit(view=view)

            participants_list = list(view.participants)

            if not participants_list:
                final_embed = giveaway_message.embeds[0]
                final_embed.description = f"**Prêmio:** {premio}\n\nNinguém participou do sorteio."
                final_embed.set_footer(text="Nenhum participante. Sorteio cancelado.")
                await giveaway_message.edit(embed=final_embed)
                await interaction.channel.send(f"🚫 O sorteio do prêmio **{premio}** foi cancelado por falta de participantes.")
                return

            winner_id = random.choice(participants_list)
            winner = interaction.guild.get_member(winner_id)

            if not winner:
                await interaction.channel.send("Erro: O vencedor saiu do servidor.")
                return

            final_embed = giveaway_message.embeds[0]
            final_embed.set_footer(text=f"Vencedor: {winner.display_name} | {rodape if rodape else ''}")
            final_embed.description = f"**Prêmio:** {premio}\n\n**🎉 O VENCEDOR É...** {winner.mention}!"
            final_embed.color = discord.Color.green()

            await giveaway_message.edit(embed=final_embed)
            await interaction.channel.send(f"🎉 Parabéns, {winner.mention}! Você ganhou o sorteio de **{premio}**!")

        except discord.NotFound:
            pass
        except Exception as e:
            bot.logger.error(f"Erro ao finalizar o sorteio: {e}")