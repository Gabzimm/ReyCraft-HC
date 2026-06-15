import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import os

# ========== IMPORTAR SISTEMA ADM ==========
from modules.adm_system import is_staff, load_adm_roles

# ========== CONFIGURAÇÕES ==========
CANAL_TICKET_ID = 1332371959308095560  # ID do canal onde o painel será postado

# URL da imagem que aparece no painel inicial
IMAGEM_PAINEL_URL = "https://cdn.discordapp.com/attachments/1386344818833363006/1516181735002472478/banner_tickets.png?ex=6a31b5c6&is=6a306446&hm=a19499c7ec159f5cb84cdc1fbe34c1de4befbaf26e759bb62815bb8d6721b5a5"

# Controle de staff assumindo tickets
staff_tickets = {}  # {staff_id: channel_id}
ultimo_chamado = {}  # {channel_id: timestamp}

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

# ========== CONFIRMAR DELEÇÃO (COM TRANSCRIPT) ==========
class ConfirmarDelecaoView(ui.View):
    def __init__(self, ticket_channel, ticket_owner_id):
        super().__init__(timeout=30)
        self.ticket_channel = ticket_channel
        self.ticket_owner_id = ticket_owner_id
    
    @ui.button(label="✅ Sim, deletar", style=ButtonStyle.danger, custom_id="deletar_confirmar")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        
        # Coletar mensagens para transcript
        messages = []
        async for msg in self.ticket_channel.history(limit=1000, oldest_first=True):
            messages.append(msg)
        
        # Salvar e enviar transcript
        transcript_file = await salvar_transcript(self.ticket_channel, messages)
        
        instrucoes = (
            "📋 **TRANSCRIPT DO SEU TICKET**\n\n"
            "Seu ticket foi deletado. Abaixo está o transcript (histórico) da conversa.\n\n"
            "**📌 COMO VISUALIZAR:**\n"
            "1️⃣ Baixe o arquivo anexado\n"
            "2️⃣ Abra com qualquer navegador (Chrome, Firefox, Edge)\n"
            "3️⃣ O transcript será exibido como uma página HTML\n\n"
            f"📅 **Ticket deletado em:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
        )
        
        try:
            user = await interaction.client.fetch_user(self.ticket_owner_id)
            with open(transcript_file, "rb") as f:
                await user.send(instrucoes, file=discord.File(f, transcript_file))
            print(f"✅ Transcript enviado para {user.name}")
        except Exception as e:
            print(f"❌ Não foi possível enviar DM: {e}")
        
        # Limpar staff_tickets
        for staff_id, channel_id in list(staff_tickets.items()):
            if channel_id == self.ticket_channel.id:
                del staff_tickets[staff_id]
        
        # Remover arquivo temporário
        try:
            os.remove(transcript_file)
        except:
            pass
        
        await self.ticket_channel.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary, custom_id="deletar_cancelar")
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()

# ========== PAINEL DO TICKET (ABERTO) ==========
class TicketPainelAbertoView(ui.View):
    """View quando o ticket está ABERTO - tem Fechar, Deletar, Assumir, Chamar"""
    def __init__(self, ticket_owner_id, ticket_channel, categoria):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
        self.categoria = categoria
        self.assumido_por = None
    
    def criar_embed(self):
        embeds = {
            "🚨 Denúncia de Jogador": discord.Embed(
                title="🚨 DENÚNCIA DE JOGADOR",
                description=(
                    "Obrigado por abrir este ticket.\n\n"
                    "Para que a denúncia seja analisada corretamente, envie todas as informações necessárias, "
                    "como o nome do jogador envolvido, horário aproximado do ocorrido e uma descrição detalhada da situação.\n\n"
                    "📌 **Mande as provas que você possui**, como prints, vídeos ou gravações. "
                    "Caso não tiver provas, essa denúncia não terá continuidade.\n\n"
                    "⚠️ Informações falsas ou denúncias feitas de má-fé poderão resultar em punições ou até mesmo em banimento.\n\n"
                    "Aguarde pacientemente até que um membro da equipe assuma seu atendimento."
                ),
                color=discord.Color.red()
            ),
            "💎 Adquirir VIP": discord.Embed(
                title="💎 ADQUIRIR VIP",
                description=(
                    "Obrigado pelo seu interesse em apoiar o servidor.\n\n"
                    "Informe qual VIP você deseja adquirir e, caso tenha alguma dúvida, descreva-a para que possamos ajudá-lo. "
                    "A equipe fornecerá todas as instruções necessárias para concluir a compra com segurança.\n\n"
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
    
    @ui.button(label="🔒 Fechar Ticket", style=ButtonStyle.gray, emoji="🔒", custom_id="ticket_fechar", row=0)
    async def fechar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        # Qualquer um pode fechar (owner ou staff)
        await interaction.response.defer()
        
        # Bloquear canal para @everyone
        overwrites = self.ticket_channel.overwrites
        overwrites[self.ticket_channel.guild.default_role].send_messages = False
        
        # Bloquear para o owner também
        try:
            member = self.ticket_channel.guild.get_member(self.ticket_owner_id)
            if member:
                overwrites[member].send_messages = False
        except:
            pass
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        # Adicionar 🔒 no nome
        if not self.ticket_channel.name.startswith("🔒"):
            await self.ticket_channel.edit(name=f"🔒{self.ticket_channel.name}")
        
        # Mensagem de ticket fechado
        embed_fechado = discord.Embed(
            title="🔒 TICKET FECHADO",
            description=f"Este ticket foi fechado por {interaction.user.mention}",
            color=discord.Color.orange()
        )
        
        # Criar view de ticket fechado (com botão reabrir)
        view_fechado = TicketPainelFechadoView(self.ticket_owner_id, self.ticket_channel, self.categoria)
        
        await interaction.message.edit(embed=embed_fechado, view=view_fechado)
        await self.ticket_channel.send(f"🔒 Ticket fechado por {interaction.user.mention}")
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", custom_id="ticket_deletar", row=0)
    async def deletar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas a equipe de suporte pode deletar tickets!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🗑️ Deletar Ticket",
            description="⚠️ **ATENÇÃO!** Isso irá deletar o ticket permanentemente!\n\nTem certeza?",
            color=discord.Color.red()
        )
        
        view = ConfirmarDelecaoView(self.ticket_channel, self.ticket_owner_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="📌 Assumir Ticket", style=ButtonStyle.success, emoji="📌", custom_id="ticket_assumir", row=1)
    async def assumir_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas a equipe de suporte pode assumir tickets!", ephemeral=True)
            return
        
        if interaction.user.id in staff_tickets:
            canal_atual = self.ticket_channel.guild.get_channel(staff_tickets[interaction.user.id])
            await interaction.response.send_message(
                f"❌ Você já está atendendo um ticket: {canal_atual.mention if canal_atual else 'Desconhecido'}\nFinalize ele antes de assumir outro!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        staff_tickets[interaction.user.id] = self.ticket_channel.id
        self.assumido_por = interaction.user
        
        embed = self.criar_embed()
        embed.description += f"\n\n**👑 Responsável:** {interaction.user.mention}"
        
        # Desabilitar apenas o botão "Assumir"
        for child in self.children:
            if child.custom_id == "ticket_assumir":
                child.disabled = True
                child.label = f"✅ Assumido por {interaction.user.display_name[:15]}"
                child.style = ButtonStyle.secondary
        
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send(f"✅ {interaction.user.mention} assumiu o ticket!", ephemeral=True)
    
    @ui.button(label="📞 Chamar Responsável", style=ButtonStyle.blurple, emoji="📞", custom_id="ticket_chamar", row=1)
    async def chamar_responsavel(self, interaction: discord.Interaction, button: ui.Button):
        if self.assumido_por is None:
            await interaction.response.send_message("❌ Ninguém assumiu este ticket ainda!", ephemeral=True)
            return
        
        canal_id = self.ticket_channel.id
        agora = datetime.now().timestamp()
        
        # Cooldown de 6 minutos
        if canal_id in ultimo_chamado:
            tempo_passado = agora - ultimo_chamado[canal_id]
            if tempo_passado < 360:
                restante = int(360 - tempo_passado)
                minutos = restante // 60
                segundos = restante % 60
                await interaction.response.send_message(
                    f"⏰ Espere {minutos} minutos e {segundos} segundos para chamar novamente!",
                    ephemeral=True
                )
                return
        
        ultimo_chamado[canal_id] = agora
        await interaction.response.defer()
        
        embed_chamada = discord.Embed(
            title="📞 CHAMANDO RESPONSÁVEL",
            description=f"{self.assumido_por.mention}\n\nO jogador {interaction.user.mention} está te chamando para finalizar o atendimento.",
            color=discord.Color.blue()
        )
        
        await self.ticket_channel.send(embed=embed_chamada)
        
        try:
            embed_dm = discord.Embed(
                title="⚠️ ATENDIMENTO PENDENTE",
                description=f"Finalize o atendimento do ticket **#{self.ticket_channel.name}**",
                color=discord.Color.red()
            )
            
            view_dm = ui.View()
            view_dm.add_item(ui.Button(label="🔗 Ir para o ticket", style=discord.ButtonStyle.link, url=self.ticket_channel.jump_url))
            
            await self.assumido_por.send(embed=embed_dm, view=view_dm)
        except:
            pass
        
        await interaction.followup.send("✅ Responsável chamado!", ephemeral=True)

# ========== PAINEL DO TICKET (FECHADO) ==========
class TicketPainelFechadoView(ui.View):
    """View quando o ticket está FECHADO - tem Reabrir (só staff), Deletar"""
    def __init__(self, ticket_owner_id, ticket_channel, categoria):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.ticket_channel = ticket_channel
        self.categoria = categoria
    
    @ui.button(label="🔓 Reabrir Ticket", style=ButtonStyle.success, emoji="🔓", custom_id="ticket_reabrir", row=0)
    async def reabrir_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode reabrir tickets!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Restaurar permissões
        overwrites = self.ticket_channel.overwrites
        
        # Liberar para @everyone (ou pelo menos para o owner)
        try:
            member = self.ticket_channel.guild.get_member(self.ticket_owner_id)
            if member:
                overwrites[member].send_messages = True
        except:
            pass
        
        await self.ticket_channel.edit(overwrites=overwrites)
        
        # Remover 🔒 do nome
        if self.ticket_channel.name.startswith("🔒"):
            novo_nome = self.ticket_channel.name[2:]
            await self.ticket_channel.edit(name=novo_nome)
        
        # Voltar para view de ticket aberto
        view_aberto = TicketPainelAbertoView(self.ticket_owner_id, self.ticket_channel, self.categoria)
        embed = view_aberto.criar_embed()
        
        await interaction.message.edit(embed=embed, view=view_aberto)
        await self.ticket_channel.send(f"🔓 **Ticket reaberto por:** {interaction.user.mention}")
    
    @ui.button(label="🗑️ Deletar Ticket", style=ButtonStyle.red, emoji="🗑️", custom_id="ticket_deletar_fechado", row=0)
    async def deletar_ticket(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas a equipe de suporte pode deletar tickets!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        embed = discord.Embed(
            title="🗑️ Deletar Ticket",
            description="⚠️ **ATENÇÃO!** Isso irá deletar o ticket permanentemente!\n\nTem certeza?",
            color=discord.Color.red()
        )
        
        view = ConfirmarDelecaoView(self.ticket_channel, self.ticket_owner_id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ========== SELECT MENU PARA ESCOLHER CATEGORIA ==========
class CategoriaSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🚨 Denúncia de Jogador", value="denuncia_jogador", emoji="🚨", description="Denuncie um jogador que está quebrando as regras"),
            discord.SelectOption(label="💎 Adquirir VIP", value="vip", emoji="💎", description="Informações sobre VIP e doações"),
            discord.SelectOption(label="⛔ Denúncia Staff", value="denuncia_staff", emoji="⛔", description="Denuncie um membro da equipe"),
            discord.SelectOption(label="📋 Outro Assunto", value="outros", emoji="📋", description="Outros assuntos não listados acima"),
        ]
        super().__init__(placeholder="🔽 Selecione o tipo de atendimento...", options=options, min_values=1, max_values=1, custom_id="categoria_select")
    
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
        
        try:
            canal_base = interaction.guild.get_channel(CANAL_TICKET_ID)
            if not canal_base:
                await interaction.followup.send("❌ Canal de tickets não encontrado! Contate um administrador.", ephemeral=True)
                return
            
            categoria_parent = canal_base.category
            
            if categoria_parent:
                for channel in categoria_parent.channels:
                    if isinstance(channel, discord.TextChannel):
                        if channel.topic and str(interaction.user.id) in channel.topic:
                            await interaction.followup.send(f"❌ Você já tem um ticket aberto: {channel.mention}", ephemeral=True)
                            return
            
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            for role_name in load_adm_roles():
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            for role in interaction.guild.roles:
                if "owner" in role.name.lower():
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            nome_canal = f"🎫-{interaction.user.name[:20]}-{categoria[:3]}"
            ticket_channel = await interaction.guild.create_text_channel(
                name=nome_canal,
                category=categoria_parent,
                overwrites=overwrites,
                topic=f"{categoria} | {interaction.user.id}",
                reason=f"Ticket criado por {interaction.user.name}"
            )
            
            painel_view = TicketPainelAbertoView(interaction.user.id, ticket_channel, nome_categoria)
            embed = painel_view.criar_embed()
            
            await ticket_channel.send(f"🎫 **Ticket aberto por:** {interaction.user.mention}", embed=embed, view=painel_view)
            await ticket_channel.send(f"📝 **Descreva sua solicitação abaixo:**")
            
            await interaction.followup.send(f"✅ Ticket criado! {ticket_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ **Erro de permissão!** Não tenho permissão para criar canais.", ephemeral=True)
        except Exception as e:
            print(f"[ERRO TICKET] {type(e).__name__}: {e}")
            await interaction.followup.send(f"❌ **Erro ao criar ticket:** {str(e)[:100]}", ephemeral=True)

# ========== VIEW PRINCIPAL ==========
class TicketAbrirView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CategoriaSelect())

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
                "**Precisa de ajuda? Selecione uma opção abaixo para abrir um ticket**\n\n"
                "Este sistema foi criado para oferecer um atendimento organizado e eficiente, sendo destinado a dúvidas, "
                "problemas relacionados ao servidor, denúncias, questões sobre cargos e outros assuntos importantes.\n\n"
                "Ao abrir um ticket, explique sua situação de forma clara e detalhada para que possamos ajudá-lo da melhor maneira possível. "
                "Quanto mais informações forem fornecidas, mais rápido será o atendimento.\n\n"
                "⚠️ **Importante:** Utilize este sistema apenas quando houver uma necessidade real. "
                "A abertura de tickets sem motivo, brincadeiras, spam ou qualquer tipo de desrespeito poderá resultar em punições ou até mesmo banimento."
            ),
            color=discord.Color.purple()
        )
        
        # Adicionar imagem abaixo do texto
        embed.set_image(url=IMAGEM_PAINEL_URL)
        embed.set_footer(text="Reycraft HC • Sistema de Suporte")
        
        view = TicketAbrirView()
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        
        print(f"✅ Painel de tickets configurado em #{ctx.channel.name}")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
    bot.add_view(TicketAbrirView())
    print("✅ Sistema de Tickets configurado!")
