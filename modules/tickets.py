import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import json
import os

# Importar sistema ADM
try:
    from modules.adm_system import is_staff
except ImportError:
    from adm_system import is_staff

# ========== CONFIGURAÇÕES ==========
TICKET_CATEGORY_ID = None
TRANSCRIPT_CHANNEL_ID = None

# Controle de staff assumindo tickets
staff_tickets = {}
ultimo_chamado = {}

# ========== FUNÇÃO PARA SALVAR TRANSCRIPT ==========
async def salvar_transcript(channel, messages):
    """Salva transcript do ticket em arquivo HTML"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{channel.name}_{timestamp}.html"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Transcript - {channel.name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #36393f; color: #fff; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{ background: #2f3136; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
        .header h1 {{ color: #7289da; margin: 0; }}
        .message {{ background: #40444b; border-radius: 10px; padding: 12px 15px; margin: 10px 0; }}
        .author {{ font-weight: bold; color: #7289da; }}
        .timestamp {{ font-size: 11px; color: #99aab5; margin-left: 10px; }}
        .content {{ margin-top: 8px; word-wrap: break-word; }}
        .embed {{ background: #2f3136; padding: 10px; border-left: 4px solid #7289da; margin: 10px 0; border-radius: 5px; }}
        .footer {{ text-align: center; margin-top: 30px; padding: 20px; background: #2f3136; border-radius: 10px; font-size: 12px; color: #99aab5; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Transcript do Ticket</h1>
            <h2>#{channel.name}</h2>
            <p>Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </div>
"""
    
    for msg in reversed(messages):
        if msg.author.bot and "Ticket aberto por" in msg.content:
            continue
            
        html_content += f"""
        <div class="message">
            <div>
                <span class="author">{msg.author.name}</span>
                <span class="timestamp">{msg.created_at.strftime('%d/%m/%Y %H:%M:%S')}</span>
            </div>
            <div class="content">{msg.content if msg.content else '📎 **Arquivo(s) enviado(s)**'}</div>
"""
        if msg.attachments:
            html_content += f'            <div class="content">📎 Anexos: {", ".join([a.filename for a in msg.attachments])}</div>\n'
        if msg.embeds:
            for embed in msg.embeds:
                html_content += f'            <div class="embed"><strong>{embed.title if embed.title else "Embed"}</strong><br>{embed.description if embed.description else ""}</div>\n'
        html_content += "        </div>\n"
    
    html_content += f"""
        <div class="footer">
            <p>🔒 Ticket fechado automaticamente</p>
            <p>Reycraft HC • Sistema de Suporte</p>
        </div>
    </div>
</body>
</html>"""
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return filename

# ========== VIEW DE REABRIR TICKET (APENAS STAFF) ==========
class TicketReabrirView(ui.View):
    def __init__(self, ticket_channel, ticket_owner_id, categoria):
        super().__init__(timeout=30)
        self.ticket_channel = ticket_channel
        self.ticket_owner_id = ticket_owner_id
        self.categoria = categoria
    
    @ui.button(label="✅ Sim, reabrir ticket", style=ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            msg = await interaction.response.send_message("❌ Apenas staff pode reabrir tickets!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        await interaction.response.defer()
        
        overwrites = self.ticket_channel.overwrites
        for target, overwrite in overwrites.items():
            if isinstance(target, discord.Role) and target.name == "@everyone":
                overwrite.send_messages = True
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        if self.ticket_channel.name.startswith("🔒"):
            novo_nome = self.ticket_channel.name[2:]
            await self.ticket_channel.edit(name=novo_nome)
        
        painel_view = TicketPainelView(self.ticket_owner_id, self.ticket_channel, self.categoria)
        embed = painel_view.criar_embed()
        
        await self.ticket_channel.send(
            f"🔓 **Ticket reaberto por:** {interaction.user.mention}",
            embed=embed,
            view=painel_view
        )
        
        await interaction.message.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()

# ========== CONFIRMAR FECHAMENTO ==========
class ConfirmarFechamentoView(ui.View):
    def __init__(self, ticket_owner_id, ticket_channel, categoria):
        super().__init__(timeout=30)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
        self.categoria = categoria
    
    @ui.button(label="✅ Sim, fechar", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        messages = []
        async for msg in self.ticket_channel.history(limit=1000, oldest_first=True):
            messages.append(msg)
        
        transcript_file = await salvar_transcript(self.ticket_channel, messages)
        
        instrucoes = (
            "📋 **TRANSCRIPT DO SEU TICKET**\n\n"
            "Seu ticket foi fechado. Abaixo está o transcript (histórico) da conversa.\n\n"
            "**📌 COMO VISUALIZAR O TRANSCRIPT:**\n"
            "1️⃣ **Baixe o arquivo** anexado abaixo\n"
            "2️⃣ **Abra seu navegador** (Chrome, Firefox, Edge, Safari)\n"
            "3️⃣ **Arraste o arquivo** para dentro do navegador OU clique duas vezes nele\n"
            "4️⃣ O transcript será exibido como uma página HTML com todo o histórico\n\n"
            "**💡 DICAS:**\n"
            "• O arquivo é um HTML (página da web) - é 100% seguro\n"
            "• Você pode salvar esta página nos favoritos se quiser guardar\n"
            "• Se tiver dificuldade, copie o arquivo para o computador e abra com qualquer navegador\n\n"
            "⚠️ Este arquivo contém todo o histórico do seu atendimento. Guarde-o se precisar consultar depois.\n\n"
            f"📅 **Ticket fechado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
        )
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            with open(transcript_file, "rb") as f:
                await user.send(instrucoes, file=discord.File(f, transcript_file))
            print(f"✅ Transcript enviado para {user.name}")
        except:
            print(f"❌ Não foi possível enviar DM para {self.ticket_owner_id}")
        
        for staff_id, channel_id in list(staff_tickets.items()):
            if channel_id == self.ticket_channel.id:
                del staff_tickets[staff_id]
        
        if not self.ticket_channel.name.startswith("🔒"):
            await self.ticket_channel.edit(name=f"🔒{self.ticket_channel.name}")
        
        overwrites = self.ticket_channel.overwrites
        overwrites[self.ticket_channel.guild.default_role].send_messages = False
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            overwrites[user].send_messages = False
        except:
            pass
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        embed_fechado = discord.Embed(
            title="🔒 TICKET FECHADO",
            description=f"Este ticket foi fechado por {interaction.user.mention}\n\nSe precisar reabrir, clique no botão abaixo (apenas staff).",
            color=discord.Color.orange()
        )
        
        reabrir_view = TicketReabrirView(self.ticket_channel, self.ticket_owner_id, self.categoria)
        
        await interaction.message.edit(view=None)
        await self.ticket_channel.send(embed=embed_fechado, view=reabrir_view)
        
        os.remove(transcript_file)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()

# ========== CONFIRMAR DELEÇÃO ==========
class ConfirmarDelecaoView(ui.View):
    def __init__(self, ticket_channel):
        super().__init__(timeout=30)
        self.ticket_channel = ticket_channel
    
    @ui.button(label="✅ Sim, deletar", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.ticket_channel.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()

# ========== PAINEL FIXO DO TICKET ==========
class TicketPainelView(ui.View):
    def __init__(self, ticket_owner_id, ticket_channel, categoria):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
        self.categoria = categoria
        self.assumido_por = None
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", row=0)
    async def fechar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🔒 Fechar Ticket",
            description="Tem certeza que deseja fechar este ticket?",
            color=discord.Color.orange()
        )
        
        view = ConfirmarFechamentoView(self.ticket_owner_id, self.ticket_channel, self.categoria)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", row=0)
    async def deletar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            msg = await interaction.response.send_message("❌ Apenas a equipe de suporte pode deletar tickets!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        embed = discord.Embed(
            title="🗑️ Deletar Ticket",
            description="⚠️ **ATENÇÃO!** Isso irá deletar o ticket permanentemente!\n\nTem certeza?",
            color=discord.Color.red()
        )
        
        view = ConfirmarDelecaoView(self.ticket_channel)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📌 Assumir Ticket", style=ButtonStyle.success, emoji="📌", row=1)
    async def assumir_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            msg = await interaction.response.send_message("❌ Apenas a equipe de suporte pode assumir tickets!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        if interaction.user.id in staff_tickets:
            canal_atual = self.ticket_channel.guild.get_channel(staff_tickets[interaction.user.id])
            msg = await interaction.response.send_message(
                f"❌ Você já está atendendo um ticket: {canal_atual.mention if canal_atual else 'Desconhecido'}\nFinalize ele antes de assumir outro!",
                ephemeral=True
            )
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        await interaction.response.defer()
        
        staff_tickets[interaction.user.id] = self.ticket_channel.id
        self.assumido_por = interaction.user
        
        embed = self.criar_embed()
        embed.description += f"\n\n**👑 Responsável:** {interaction.user.mention}"
        
        self.clear_items()
        self.add_item(ui.Button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", row=0, custom_id="fechar"))
        self.add_item(ui.Button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", row=0, custom_id="deletar"))
        self.add_item(ui.Button(label="📞 Chamar Responsável", style=ButtonStyle.blurple, emoji="📞", row=1, custom_id="chamar"))
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send(f"✅ {interaction.user.mention} assumiu o ticket!")
    
    @ui.button(label="📞 Chamar Responsável", style=ButtonStyle.blurple, emoji="📞", row=1)
    async def chamar_responsavel(self, interaction: discord.Interaction, button: ui.Button):
        if self.assumido_por is None:
            msg = await interaction.response.send_message("❌ Ninguém assumiu este ticket ainda!", ephemeral=True)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        canal_id = self.ticket_channel.id
        agora = datetime.now().timestamp()
        
        if canal_id in ultimo_chamado:
            tempo_passado = agora - ultimo_chamado[canal_id]
            if tempo_passado < 360:
                restante = int(360 - tempo_passado)
                minutos = restante // 60
                segundos = restante % 60
                msg = await interaction.response.send_message(
                    f"⏰ Espere {minutos} minutos e {segundos} segundos para chamar novamente!",
                    ephemeral=True
                )
                await asyncio.sleep(5)
                await msg.delete()
                return
        
        ultimo_chamado[canal_id] = agora
        
        await interaction.response.defer()
        
        embed_chamada = discord.Embed(
            title="📞 CHAMANDO RESPONSÁVEL",
            description=(
                f"{self.assumido_por.mention}\n\n"
                f"O jogador {interaction.user.mention} está te chamando para finalizar o atendimento."
            ),
            color=discord.Color.blue()
        )
        
        await self.ticket_channel.send(embed=embed_chamada)
        
        try:
            embed_dm = discord.Embed(
                title="⚠️ ATENDIMENTO PENDENTE",
                description=f"Finalize o atendimento do ticket **#{self.ticket_channel.name}**",
                color=discord.Color.red()
            )
            
            view = ui.View()
            view.add_item(ui.Button(label="🔗 Ir para o ticket", style=discord.ButtonStyle.link, url=self.ticket_channel.jump_url))
            
            await self.assumido_por.send(embed=embed_dm, view=view)
        except:
            pass
        
        await interaction.followup.send("✅ Responsável chamado!", ephemeral=True)
    
    def criar_embed(self):
        embeds = {
            "🚨 Denúncia de Jogador": discord.Embed(
                title="🚨 DENÚNCIA DE JOGADOR",
                description=(
                    "Obrigado por abrir este ticket.\n\n"
                    "Para que a denúncia seja analisada corretamente, envie todas as informações necessárias, "
                    "como o nome do jogador envolvido, aproximado do ocorrido e uma descrição detalhada da situação.\n\n"
                    "📌 **Mande as provas que você possui**, como prints, vídeos ou gravações, envie-as neste ticket. "
                    "Caso não tiver provas essa denúncia não ira dar continuidade\n\n"
                    "⚠️ Informações falsas ou denúncias feitas de má-fé poderão resultar em punições ou até mesmo em banimento.\n\n"
                    "Aguarde pacientemente até que um membro da equipe assuma seu atendimento."
                ),
                color=discord.Color.red()
            ),
            "💎 Adquirir VIP": discord.Embed(
                title="💎 ADQUIRIR VIP",
                description=(
                    "Obrigado pelo seu interesse em apoiar o servidor.\n\n"
                    "Informe qual VIP você deseja adquirir e, caso tenha alguma dúvida, descreva-a para que possamos ajudá-lo, "
                    "a equipe fornecerá todas as instruções necessárias para concluir a compra com segurança.\n\n"
                    "⚠️ Nunca realize pagamentos sem a confirmação e orientação da equipe oficial do servidor.\n\n"
                    "Aguarde até que um membro da equipe assuma seu atendimento."
                ),
                color=discord.Color.gold()
            ),
            "⛔ Denúncia Staff": discord.Embed(
                title="⛔ DENÚNCIA CONTRA STAFF",
                description=(
                    "Obrigado por abrir este ticket.\n\n"
                    "Caso deseje denunciar um membro da equipe, descreva a situação com clareza e forneça o máximo de informações possível, "
                    "incluindo o nome do staff envolvido, a data, o horário aproximado e o ocorrido.\n\n"
                    "📌 **Envie o máximo de provas que você tem**, como prints, vídeos ou gravações.\n\n"
                    "⚠️ Denúncias falsas, acusações sem fundamento ou feitas com a intenção de prejudicar alguém poderão resultar em BANIMENTO PERMANENTE.\n\n"
                    "Aguarde até que sua solicitação seja analisada pela administração."
                ),
                color=discord.Color.dark_red()
            ),
            "📋 Outro Assunto": discord.Embed(
                title="📋 OUTROS ASSUNTOS",
                description=(
                    "Obrigado por abrir este ticket.\n\n"
                    "Utilize esta opção para assuntos que não se enquadram nas demais categorias disponíveis.\n\n"
                    "Descreva sua solicitação de forma clara e detalhada para que a equipe consiga entender sua situação "
                    "e prestar o melhor atendimento possível.\n\n"
                    "⚠️ Evite abrir tickets desnecessários, enviar spam ou utilizar este sistema de forma inadequada, "
                    "isso pode e irá resultar em punições e até mesmo banimento.\n\n"
                    "Aguarde até que um membro da equipe assuma seu atendimento."
                ),
                color=discord.Color.blue()
            )
        }
        return embeds.get(self.categoria, embeds["📋 Outro Assunto"])

# ========== SELECT MENU PARA ESCOLHER CATEGORIA ==========
class CategoriaSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🚨 Denúncia de Jogador", value="denuncia_jogador", emoji="🚨", description="Denuncie um jogador que está quebrando as regras"),
            discord.SelectOption(label="💎 Adquirir VIP", value="vip", emoji="💎", description="Informações sobre VIP e doações"),
            discord.SelectOption(label="⛔ Denúncia Staff", value="denuncia_staff", emoji="⛔", description="Denuncie um membro da equipe"),
            discord.SelectOption(label="📋 Outro Assunto", value="outros", emoji="📋", description="Outros assuntos não listados acima"),
        ]
        super().__init__(placeholder="🔽 Selecione o tipo de atendimento...", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        
        nome_categoria = {
            "denuncia_jogador": "🚨 Denúncia de Jogador",
            "vip": "💎 Adquirir VIP", 
            "denuncia_staff": "⛔ Denúncia Staff",
            "outros": "📋 Outro Assunto"
        }.get(categoria, "📋 Outro Assunto")
        
        await self.criar_ticket(interaction, categoria, nome_categoria)
    
    async def criar_ticket(self, interaction: discord.Interaction, categoria, nome_categoria):
        await interaction.response.defer(ephemeral=True)
        
        categoria_parent = interaction.channel.category
        for channel in categoria_parent.channels:
            if channel.topic and str(interaction.user.id) in channel.topic:
                await interaction.followup.send(f"❌ Você já tem um ticket aberto: {channel.mention}", ephemeral=True)
                return
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        
        from modules.adm_system import load_adm_roles
        for role_name in load_adm_roles():
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        nome_canal = f"🎫-{interaction.user.name[:20]}-{categoria[:3]}"
        ticket_channel = await interaction.guild.create_text_channel(
            name=nome_canal,
            category=interaction.channel.category,
            overwrites=overwrites,
            topic=f"{categoria} | {interaction.user.id}",
            reason=f"Ticket criado por {interaction.user.name}"
        )
        
        painel_view = TicketPainelView(interaction.user.id, ticket_channel, nome_categoria)
        embed = painel_view.criar_embed()
        
        await ticket_channel.send(f"🎫 **Ticket aberto por:** {interaction.user.mention}", embed=embed, view=painel_view)
        await ticket_channel.send(f"📝 **Descreva sua solicitação abaixo:**")
        
        await interaction.followup.send(f"✅ Ticket criado! {ticket_channel.mention}", ephemeral=True)

# ========== VIEW PRINCIPAL COM SELECT MENU ==========
class TicketAbrirView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoriaSelect())
    
    @ui.button(label="🎫 Abrir Ticket", style=ButtonStyle.primary, emoji="🎫", custom_id="abrir_ticket", row=1)
    async def abrir_ticket(self, interaction: discord.Interaction, button: ui.Button):
        # Apenas mostrar o select menu que já está na view
        pass

# ========== COG PRINCIPAL ==========
class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Tickets carregado!")
    
    @commands.command(name="setup_tickets")
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        """Configura o painel de tickets"""
        
        embed = discord.Embed(
            title="🎫 CENTRAL DE ATENDIMENTO",
            description=(
                "**Precisa de ajuda? Clique no botão abaixo para abrir um ticket e escolha a opção que atenda seu atendimento**\n\n"
                "Este sistema foi criado para oferecer um atendimento organizado e eficiente, sendo destinado a dúvidas, "
                "problemas relacionados ao servidor, denúncias, questões sobre cargos e outros assuntos importantes.\n\n"
                "Ao abrir um ticket, explique sua situação de forma clara e detalhada para que possamos ajudá-lo da melhor maneira possível. "
                "Quanto mais informações forem fornecidas, mais rápido será o atendimento.\n\n"
                "⚠️ **Importante:** Utilize este sistema apenas quando houver uma necessidade real. "
                "A abertura de tickets sem motivo, brincadeiras, spam ou qualquer tipo de desrespeito poderá resultar em punições ou até mesmo banimento."
            ),
            color=discord.Color.purple()
        )
        
        view = TicketAbrirView()
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        
        print(f"✅ Painel de tickets configurado em #{ctx.channel.name}")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    bot.add_view(TicketAbrirView())
    print("✅ Sistema de Tickets configurado!")
