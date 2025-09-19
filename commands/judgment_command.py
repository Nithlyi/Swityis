import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class JudgmentView(discord.ui.View):
    def __init__(self, bot, member, punishment_type, punishment_time, reason):
        super().__init__()
        self.bot = bot
        self.member = member
        self.punishment_type = punishment_type
        self.punishment_time = punishment_time
        self.reason = reason
        self.votes_yes = 0
        self.votes_no = 0
        self.voters = set()

    @discord.ui.button(label="Sim", style=discord.ButtonStyle.green)
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            await interaction.response.send_message("Você já votou.", ephemeral=True)
            return
        
        self.voters.add(interaction.user.id)
        self.votes_yes += 1
        await interaction.response.send_message("Seu voto foi registrado!", ephemeral=True)
        await self.update_view()

    @discord.ui.button(label="Não", style=discord.ButtonStyle.red)
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            await interaction.response.send_message("Você já votou.", ephemeral=True)
            return
        
        self.voters.add(interaction.user.id)
        self.votes_no += 1
        await interaction.response.send_message("Seu voto foi registrado!", ephemeral=True)
        await self.update_view()

    async def update_view(self):
        # Atualiza o contador de votos nos botões
        self.children[0].label = f"Sim ({self.votes_yes})"
        self.children[1].label = f"Não ({self.votes_no})"
        
        # Envia a nova visualização
        await asyncio.sleep(2)  # Adiciona um delay de 2 segundos
        await self.message.edit(view=self)

    async def on_timeout(self):
        # Desativa os botões e decide o resultado
        for button in self.children:
            button.disabled = True
        
        await self.message.edit(view=self)

        result_message = ""
        if self.votes_yes > self.votes_no:
            result_message = f"O julgamento de {self.member.mention} foi **aprovado**! Executando a punição de `{self.punishment_type}`."
            # AQUI VOCÊ APLICA A PUNIÇÃO
            # Ex: await self.member.kick()
        else:
            result_message = f"O julgamento de {self.member.mention} foi **rejeitado**. A punição não será aplicada."

        await self.message.channel.send(result_message)

def setup(tree: app_commands.CommandTree, bot: commands.Bot):
    @tree.command(name="julgamento", description="Inicia um julgamento público por votação.")
    @app_commands.describe(
        usuario="O usuário a ser julgado.",
        punicao="O tipo de punição.",
        tempo_punicao="Tempo da punição (ex: 7d para 7 dias). Opcional.",
        motivo="O motivo do julgamento."
    )
    @app_commands.choices(
        punicao=[
            app_commands.Choice(name="Mute", value="mute"),
            app_commands.Choice(name="Kick", value="kick"),
            app_commands.Choice(name="Ban", value="ban")
        ]
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def judgment(
        interaction: discord.Interaction,
        usuario: discord.Member,
        punicao: app_commands.Choice[str],
        tempo_punicao: str = None,
        motivo: str = "Motivo não especificado."
    ):
        embed = discord.Embed(
            title=f"🚨 Julgamento Público: {usuario.display_name}",
            description=f"Um julgamento foi iniciado contra {usuario.mention}.",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.add_field(name="Punição Proposta", value=punicao.name, inline=True)
        if tempo_punicao:
            embed.add_field(name="Duração", value=tempo_punicao, inline=True)
        
        view = JudgmentView(bot, usuario, punicao.value, tempo_punicao, motivo)
        await interaction.response.send_message(
            f"Julgamento de {usuario.mention} iniciado! Votem nos botões abaixo.",
            embed=embed,
            view=view
        )
        
        # Salva a mensagem para ser atualizada
        view.message = await interaction.original_response()