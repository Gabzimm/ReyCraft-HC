import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
import sys
import os

# Adicionar caminho para importar utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar sistema de memória
from utils.memory import load_guild_data, save_guild_data

# ========== CONFIGURAÇÕES ==========
CANAL_PAINEL_ID = 1516443229770350623 
CARGO_BASE_ID = 1516526627977302166
CATEGORIA_BASE_ID = 1516442856116584608 # ID da CATEGORIA base
LIMITE_PADRAO = 8

EMOJI_CLANS = "<:Clans:1516442579489788088>"

# ========== FUNÇÕES AUXILIARES ==========
def carregar_clans(guild_id):
    return load_guild_data(guild_id, "clans", {})

def salvar_clans(guild_id, clans):
    save_guild_data(guild_id, "clans", clans)

def tem_cla(member: discord.Member) -> bool:
    if not member:
        return False
    
    clans = carregar_clans(member.guild.id)
    for clan_data in clans.values():
        cargo_id = clan_data.get("cargo_id")
        if cargo_id:
            role = member.guild.get_role(cargo_id)
            if role and role in member.roles:
                return True
    
    for role in member.roles:
        if role.name.startswith("・ "):
            return True
    
    return False

def is_staff(member: discord.Member) -> bool:
    try:
        from modules.adm_system import is_staff as adm_is_staff
        return adm_is_staff(member)
    except:
        return member.guild_permissions.administrator

# ========== MODAL NOME DO CLÃ ==========
class ModalNomeCla(ui.Modal, title="⚔️ Criar Clã"):
    nome_cla = ui.TextInput(
        label="Nome do seu clã:",
        placeholder="Ex: Dragões de Fogo",
        required=True,
        max_length=50,
        min_length=3
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        nome = self.nome_cla.value.strip()
        
        if tem_cla(interaction.user):
            await interaction.response.send_message("❌ Você já pertence a um clã!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        for clan_data in clans.values():
            if clan_data["nome"].lower() == nome.lower():
                await interaction.response.send_message(f"❌ Já existe um clã com o nome `{nome}`!", ephemeral=True)
                return
        
        await interaction.response.defer(ephemeral=True)
        
        cargo_base = interaction.guild.get_role(CARGO_BASE_ID)
        if not cargo_base:
            await interaction.followup.send("❌ Cargo base não encontrado!", ephemeral=True)
            return
        
        try:
            cargo_cla = await interaction.guild.create_role(
                name=f"・ {nome}",
                permissions=cargo_base.permissions,
                color=discord.Color.from_rgb(88, 101, 242),
                hoist=True,
                mentionable=True,
                reason=f"Clã criado por {interaction.user.name}"
            )
            
            await interaction.user.add_roles(cargo_cla)
            
            clan_id = str(interaction.user.id)
            clans[clan_id] = {
                "nome": nome,
                "cargo_id": cargo_cla.id,
                "dono_id": interaction.user.id,
                "limite": LIMITE_PADRAO,
                "membros": [interaction.user.id],
                "canais": {},
                "categoria_id": None,
                "criado_em": datetime.now().isoformat()
            }
            salvar_clans(interaction.guild.id, clans)
            
            embed = discord.Embed(
                title="✅ Clã criado!",
                description=f"**{nome}** criado com sucesso!\nCargo: {cargo_cla.mention}\n\nAgora configure seus canais:",
                color=discord.Color.green()
            )
            
            view = BotaoCanalTextoView(self.cog, nome, cargo_cla)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erro ao criar clã: {e}")
            await interaction.followup.send(f"❌ Erro: {str(e)[:100]}", ephemeral=True)

# ========== BOTÃO CANAL DE TEXTO ==========
class BotaoCanalTextoView(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
    
    @ui.button(label="📝 Nomear Canal de Texto", style=ButtonStyle.primary, emoji="📝")
    async def abrir_modal(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalTexto(self.cog, self.nome_cla, self.cargo_cla)
        await interaction.response.send_modal(modal)

# ========== MODAL CANAL DE TEXTO ==========
class ModalCanalTexto(ui.Modal, title="📝 Canal de Texto"):
    nome_canal = ui.TextInput(
        label="Nome do canal de texto:",
        placeholder="Ex: 💬-chat-do-cla",
        required=True,
        max_length=50,
        min_length=3
    )
    
    def __init__(self, cog, nome_cla, cargo_cla):
        super().__init__()
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
    
    async def on_submit(self, interaction: discord.Interaction):
        nome_texto = self.nome_canal.value.strip().replace(" ", "-").lower()
        
        await interaction.response.defer(ephemeral=True)
        
        clans = carregar_clans(interaction.guild.id)
        clan_id = None
        for cid, cdata in clans.items():
            if cdata["cargo_id"] == self.cargo_cla.id:
                clan_id = cid
                break
        
        if clan_id:
            clans[clan_id]["canais"]["texto_nome"] = nome_texto
            salvar_clans(interaction.guild.id, clans)
        
        embed = discord.Embed(
            title="🎙️ Canal de Voz 1",
            description=f"Canal de texto: **{nome_texto}**\n\nEscolha o nome do primeiro canal de voz:",
            color=discord.Color.blue()
        )
        
        view = BotaoCanalVoz1View(self.cog, self.nome_cla, self.cargo_cla, nome_texto)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ========== BOTÃO CANAL DE VOZ 1 ==========
class BotaoCanalVoz1View(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
    
    @ui.button(label="🎙️ Nomear Voz 1", style=ButtonStyle.primary, emoji="🎙️")
    async def abrir_modal(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalVoz1(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto)
        await interaction.response.send_modal(modal)

# ========== MODAL CANAL DE VOZ 1 ==========
class ModalCanalVoz1(ui.Modal, title="🎙️ Canal de Voz 1"):
    nome_canal = ui.TextInput(
        label="Nome do primeiro canal de voz:",
        placeholder="Ex: 🔉-voz-do-cla",
        required=True,
        max_length=50,
        min_length=3
    )
    
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto):
        super().__init__()
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
    
    async def on_submit(self, interaction: discord.Interaction):
        nome_voz1 = self.nome_canal.value.strip().replace(" ", "-").lower()
        
        await interaction.response.defer(ephemeral=True)
        
        clans = carregar_clans(interaction.guild.id)
        clan_id = None
        for cid, cdata in clans.items():
            if cdata["cargo_id"] == self.cargo_cla.id:
                clan_id = cid
                break
        
        if clan_id:
            clans[clan_id]["canais"]["voz1_nome"] = nome_voz1
            salvar_clans(interaction.guild.id, clans)
        
        embed = discord.Embed(
            title="🎙️ Canal de Voz 2",
            description=f"Canal de texto: **{self.nome_texto}**\nCanal de voz 1: **{nome_voz1}**\n\nEscolha o nome do segundo canal de voz:",
            color=discord.Color.blue()
        )
        
        view = BotaoCanalVoz2View(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto, nome_voz1)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ========== BOTÃO CANAL DE VOZ 2 ==========
class BotaoCanalVoz2View(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto, nome_voz1):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
        self.nome_voz1 = nome_voz1
    
    @ui.button(label="🎙️ Nomear Voz 2", style=ButtonStyle.primary, emoji="🎙️")
    async def abrir_modal(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalVoz2(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto, self.nome_voz1)
        await interaction.response.send_modal(modal)

# ========== MODAL CANAL DE VOZ 2 ==========
class ModalCanalVoz2(ui.Modal, title="🎙️ Canal de Voz 2"):
    nome_canal = ui.TextInput(
        label="Nome do segundo canal de voz:",
        placeholder="Ex: 🔊-voz-do-cla-2",
        required=True,
        max_length=50,
        min_length=3
    )
    
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto, nome_voz1):
        super().__init__()
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
        self.nome_voz1 = nome_voz1
    
    async def on_submit(self, interaction: discord.Interaction):
        nome_voz2 = self.nome_canal.value.strip().replace(" ", "-").lower()
        
        await interaction.response.defer(ephemeral=True)
        
        if self.cog is None:
            await interaction.followup.send("❌ Erro interno!", ephemeral=True)
            return
        
        await self.cog.criar_canais_cla(
            interaction=interaction,
            user=interaction.user,
            nome_cla=self.nome_cla,
            cargo_cla=self.cargo_cla,
            nome_texto=self.nome_texto,
            nome_voz1=self.nome_voz1,
            nome_voz2=nome_voz2
        )

# ========== VIEW DE CONVITE NO CANAL PRIVADO ==========
class ConviteClaView(ui.View):
    def __init__(self, clan_id, guild_id, convidado_id, dono_id, dono_nome, canal_privado_id, cog):
        super().__init__(timeout=300)
        self.clan_id = clan_id
        self.guild_id = guild_id
        self.convidado_id = convidado_id
        self.dono_id = dono_id
        self.dono_nome = dono_nome
        self.canal_privado_id = canal_privado_id
        self.cog = cog
    
    @ui.button(label="✅ Aceitar", style=ButtonStyle.success, emoji="✅")
    async def aceitar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.convidado_id:
            await interaction.response.send_message("❌ Este convite não é para você!", ephemeral=True)
            return
        
        guild = interaction.guild
        clans = carregar_clans(guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Este clã não existe mais!", ephemeral=True)
            return
        
        if tem_cla(interaction.user):
            await interaction.response.send_message("❌ Você já pertence a um clã!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) >= clan_data["limite"]:
            await interaction.response.send_message(f"❌ O clã atingiu o limite de {clan_data['limite']} membros!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Adicionar ao clã
        cargo = guild.get_role(clan_data["cargo_id"])
        if cargo:
            await interaction.user.add_roles(cargo)
        
        clan_data["membros"].append(interaction.user.id)
        salvar_clans(guild.id, clans)
        
        # ✅ Aceitou (confirmação) - CONVIDADO - EFÊMERA
        await interaction.followup.send(
            f"✅ Você entrou no clã **{clan_data['nome']}**!",
            ephemeral=True
        )
        
        # DELETAR CANAL PRIVADO
        canal_privado = guild.get_channel(self.canal_privado_id)
        if canal_privado:
            await canal_privado.delete()
        
        # ✅ Aceitou (notificação) - DONO - EFÊMERA no canal do clã
        canais = clan_data.get("canais", {})
        texto_id = canais.get("texto_id")
        if texto_id:
            canal_cla = guild.get_channel(texto_id)
            if canal_cla:
                embed_dono = discord.Embed(
                    title="✅ Convite Aceito!",
                    description=f"{interaction.user.mention} **aceitou** seu convite e entrou no clã **{clan_data['nome']}**!",
                    color=discord.Color.green()
                )
                embed_dono.set_footer(text=f"📊 {len(clan_data['membros'])}/{clan_data['limite']} membros")
                await canal_cla.send(
                    content=f"||{interaction.guild.get_member(self.dono_id).mention if interaction.guild.get_member(self.dono_id) else ''}||",
                    embed=embed_dono,
                    delete_after=15
                )
        
        # ✅ Aceitou (público) - TODOS - Temporária (30s)
        if texto_id:
            canal = guild.get_channel(texto_id)
            if canal:
                await canal.send(
                    f"✅ {interaction.user.mention} **aceitou** o convite e entrou no clã!\n"
                    f"📊 {len(clan_data['membros'])}/{clan_data['limite']} membros",
                    delete_after=30
                )
    
    @ui.button(label="❌ Recusar", style=ButtonStyle.danger, emoji="❌")
    async def recusar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.convidado_id:
            await interaction.response.send_message("❌ Este convite não é para você!", ephemeral=True)
            return
        
        guild = interaction.guild
        clans = carregar_clans(guild.id)
        clan_data = clans.get(self.clan_id)
        
        await interaction.response.defer(ephemeral=True)
        
        # ❌ Recusou (confirmação) - CONVIDADO - EFÊMERA
        await interaction.followup.send(
            f"❌ Você recusou o convite para entrar no clã **{clan_data['nome'] if clan_data else 'desconhecido'}**.",
            ephemeral=True
        )
        
        # DELETAR CANAL PRIVADO
        canal_privado = guild.get_channel(self.canal_privado_id)
        if canal_privado:
            await canal_privado.delete()
        
        # ❌ Recusou (notificação) - DONO - EFÊMERA no canal do clã
        if clan_data:
            canais = clan_data.get("canais", {})
            texto_id = canais.get("texto_id")
            if texto_id:
                canal_cla = guild.get_channel(texto_id)
                if canal_cla:
                    embed_dono = discord.Embed(
                        title="❌ Convite Recusado",
                        description=(
                            f"O jogador {interaction.user.mention} **recusou** seu convite "
                            f"para entrar no clã **{clan_data['nome']}**.\n\n"
                            f"💡 Você precisará enviar o convite novamente."
                        ),
                        color=discord.Color.red()
                    )
                    await canal_cla.send(
                        content=f"||{interaction.guild.get_member(self.dono_id).mention if interaction.guild.get_member(self.dono_id) else ''}||",
                        embed=embed_dono,
                        delete_after=15
                    )
    
    async def on_timeout(self):
        """Quando o convite expira (5 minutos)"""
        try:
            guild = self.cog.bot.get_guild(self.guild_id)
            if guild:
                canal_privado = guild.get_channel(self.canal_privado_id)
                if canal_privado:
                    await canal_privado.delete()
                
                clans = carregar_clans(guild.id)
                clan_data = clans.get(self.clan_id)
                if clan_data:
                    canais = clan_data.get("canais", {})
                    texto_id = canais.get("texto_id")
                    if texto_id:
                        canal_cla = guild.get_channel(texto_id)
                        if canal_cla:
                            embed = discord.Embed(
                                title="⏰ Convite Expirado",
                                description=f"O convite para o clã **{clan_data['nome']}** expirou após 5 minutos.",
                                color=discord.Color.orange()
                            )
                            await canal_cla.send(
                                content=f"||{guild.get_member(self.dono_id).mention if guild.get_member(self.dono_id) else ''}||",
                                embed=embed,
                                delete_after=15
                            )
        except:
            pass
        
        self.stop()


# ========== VIEW DE SELEÇÃO DE MEMBRO PARA CONVIDAR ==========
class SelecionarMembroConviteView(ui.View):
    def __init__(self, clan_id, guild, dono_id, cog, pagina=0):
        super().__init__(timeout=180)
        self.clan_id = clan_id
        self.guild = guild
        self.dono_id = dono_id
        self.cog = cog
        self.pagina = pagina
        
        clans = carregar_clans(guild.id)
        clan_data = clans.get(clan_id)
        membros_atuais = clan_data["membros"] if clan_data else []
        
        self.membros_disponiveis = []
        for member in guild.members:
            if not member.bot and not tem_cla(member) and member.id not in membros_atuais:
                self.membros_disponiveis.append(member)
        
        self.membros_disponiveis.sort(key=lambda m: m.display_name.lower())
        
        self.por_pagina = 24
        self.total_paginas = max(1, (len(self.membros_disponiveis) + self.por_pagina - 1) // self.por_pagina)
        
        inicio = pagina * self.por_pagina
        fim = min(inicio + self.por_pagina, len(self.membros_disponiveis))
        membros_pagina = self.membros_disponiveis[inicio:fim]
        
        select = ui.Select(
            placeholder=f"📨 Convidar jogador (Página {pagina + 1}/{self.total_paginas})",
            min_values=1,
            max_values=1,
            row=0
        )
        
        if membros_pagina:
            for member in membros_pagina:
                select.add_option(
                    label=member.display_name[:100],
                    value=str(member.id),
                    description=f"@{member.name}",
                    emoji="👤"
                )
            select.callback = self.selecionar_callback
        else:
            select.placeholder = "❌ Nenhum jogador disponível"
            select.disabled = True
        
        self.add_item(select)
        
        if self.total_paginas > 1:
            if pagina > 0:
                btn_anterior = ui.Button(label="◀️ Anterior", style=ButtonStyle.secondary, row=1)
                btn_anterior.callback = self.pagina_anterior
                self.add_item(btn_anterior)
            
            if pagina < self.total_paginas - 1:
                btn_proxima = ui.Button(label="Próxima ▶️", style=ButtonStyle.secondary, row=1)
                btn_proxima.callback = self.pagina_proxima
                self.add_item(btn_proxima)
    
    async def selecionar_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        membro_id = int(self.children[0].values[0])
        member = self.guild.get_member(membro_id)
        
        if not member:
            await interaction.response.send_message("❌ Jogador não encontrado!", ephemeral=True)
            return
        
        if tem_cla(member):
            await interaction.response.send_message("❌ Já pertence a um clã!", ephemeral=True)
            return
        
        clans = carregar_clans(self.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) >= clan_data["limite"]:
            await interaction.response.send_message(f"❌ Limite atingido ({clan_data['limite']})!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            categoria_base = self.guild.get_channel(CATEGORIA_BASE_ID)
            if not categoria_base:
                await interaction.followup.send("❌ Categoria base não encontrada!", ephemeral=True)
                return
            
            # Criar canal privado
            overwrites = {
                self.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Adicionar permissão para ADMs e cargo máximo
            try:
                from modules.adm_system import load_adm_roles, load_cargo_max
                
                # ADMs
                adm_roles = load_adm_roles(self.guild.id)
                for role_name in adm_roles:
                    role = discord.utils.get(self.guild.roles, name=role_name)
                    if role:
                        overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                # Cargo máximo
                cargo_max_nome = load_cargo_max(self.guild.id)
                cargo_max = discord.utils.get(self.guild.roles, name=cargo_max_nome)
                if cargo_max:
                    overwrites[cargo_max] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            except:
                pass
            
            nome_canal = f"📨-convite-para-{member.display_name.lower().replace(' ', '-')[:30]}"
            
            canal_privado = await self.guild.create_text_channel(
                name=nome_canal,
                category=categoria_base,
                overwrites=overwrites,
                topic=f"Convite para {member.display_name} entrar no clã {clan_data['nome']} | Expira em 5 minutos"
            )
            
            embed_convite = discord.Embed(
                title="📨 Convite de Clã",
                description=(
                    f"Você recebeu um convite de {interaction.user.mention}\n"
                    f"para entrar no clã **{clan_data['nome']}**\n\n"
                    f"Você deseja entrar nele?"
                ),
                color=discord.Color.blue()
            )
            embed_convite.set_footer(text=f"Clã: {clan_data['nome']} | O convite expira em 5 minutos")
            
            view_convite = ConviteClaView(
                self.clan_id,
                self.guild.id,
                member.id,
                interaction.user.id,
                interaction.user.display_name,
                canal_privado.id,
                self.cog
            )
            
            await canal_privado.send(
                content=f"{member.mention} {interaction.user.mention}",
                embed=embed_convite,
                view=view_convite
            )
            
            await interaction.followup.send(
                f"📨 Convite enviado para {member.mention}!\n\n"
                f"📁 Canal criado: {canal_privado.mention}\n"
                f"⏳ **Aguarde até que {member.display_name} aceite o convite.**\n"
                f"💡 Caso ele recuse ou expire (5min), o canal será deletado automaticamente.\n"
                f"🔄 Se recusar, você precisará enviar o convite novamente.",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao criar canal de convite: {e}", ephemeral=True)
    
    async def pagina_anterior(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        await interaction.response.defer()
        nova_view = SelecionarMembroConviteView(self.clan_id, self.guild, self.dono_id, self.cog, self.pagina - 1)
        await interaction.edit_original_response(view=nova_view)
    
    async def pagina_proxima(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        await interaction.response.defer()
        nova_view = SelecionarMembroConviteView(self.clan_id, self.guild, self.dono_id, self.cog, self.pagina + 1)
        await interaction.edit_original_response(view=nova_view)


# ========== VIEW DE SELEÇÃO DE MEMBRO (REMOVER) ==========
class SelecionarMembroRemoveView(ui.View):
    def __init__(self, clan_id, guild, dono_id, pagina=0):
        super().__init__(timeout=180)
        self.clan_id = clan_id
        self.guild = guild
        self.dono_id = dono_id
        self.pagina = pagina
        
        clans = carregar_clans(guild.id)
        clan_data = clans.get(clan_id)
        
        self.membros_cla = []
        if clan_data:
            for membro_id in clan_data["membros"]:
                if membro_id != dono_id:
                    member = guild.get_member(membro_id)
                    if member:
                        self.membros_cla.append(member)
        
        self.membros_cla.sort(key=lambda m: m.display_name.lower())
        
        self.por_pagina = 24
        self.total_paginas = max(1, (len(self.membros_cla) + self.por_pagina - 1) // self.por_pagina)
        
        inicio = pagina * self.por_pagina
        fim = min(inicio + self.por_pagina, len(self.membros_cla))
        membros_pagina = self.membros_cla[inicio:fim]
        
        select = ui.Select(
            placeholder=f"🔍 Membros do clã (Página {pagina + 1}/{self.total_paginas})",
            min_values=1,
            max_values=1,
            row=0
        )
        
        if membros_pagina:
            for member in membros_pagina:
                select.add_option(
                    label=member.display_name[:100],
                    value=str(member.id),
                    description=f"@{member.name}",
                    emoji="👤"
                )
            select.callback = self.selecionar_callback
        else:
            select.placeholder = "❌ Nenhum membro para remover"
            select.disabled = True
        
        self.add_item(select)
        
        if self.total_paginas > 1:
            if pagina > 0:
                btn_anterior = ui.Button(label="◀️ Anterior", style=ButtonStyle.secondary, row=1)
                btn_anterior.callback = self.pagina_anterior
                self.add_item(btn_anterior)
            
            if pagina < self.total_paginas - 1:
                btn_proxima = ui.Button(label="Próxima ▶️", style=ButtonStyle.secondary, row=1)
                btn_proxima.callback = self.pagina_proxima
                self.add_item(btn_proxima)
    
    async def selecionar_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        membro_id = int(self.children[0].values[0])
        member = self.guild.get_member(membro_id)
        
        if not member:
            await interaction.response.send_message("❌ Jogador não encontrado!", ephemeral=True)
            return
        
        clans = carregar_clans(self.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        cargo = self.guild.get_role(clan_data["cargo_id"])
        if cargo:
            await member.remove_roles(cargo)
        
        clan_data["membros"].remove(membro_id)
        salvar_clans(self.guild.id, clans)
        
        for item in self.children:
            item.disabled = True
        self.children[0].placeholder = f"✅ {member.display_name} removido!"
        
        await interaction.edit_original_response(view=self)
        
        await interaction.followup.send(
            f"✅ {member.mention} removido do clã **{clan_data['nome']}**!\n"
            f"📊 {len(clan_data['membros'])}/{clan_data['limite']}",
            ephemeral=True
        )
    
    async def pagina_anterior(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        await interaction.response.defer()
        nova_view = SelecionarMembroRemoveView(self.clan_id, self.guild, self.dono_id, self.pagina - 1)
        await interaction.edit_original_response(view=nova_view)
    
    async def pagina_proxima(self, interaction: discord.Interaction):
        if interaction.user.id != self.dono_id:
            await interaction.response.send_message("❌ Apenas o dono do clã!", ephemeral=True)
            return
        
        await interaction.response.defer()
        nova_view = SelecionarMembroRemoveView(self.clan_id, self.guild, self.dono_id, self.pagina + 1)
        await interaction.edit_original_response(view=nova_view)


# ========== CONFIRMAR EXCLUSÃO ==========
class ConfirmarExclusaoView(ui.View):
    def __init__(self, cog, clan_id, guild_id):
        super().__init__(timeout=30)
        self.cog = cog
        self.clan_id = clan_id
        self.guild_id = guild_id
    
    @ui.button(label="✅ Sim, excluir tudo!", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.cog.excluir_cla(interaction, self.clan_id)
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()


# ========== CONFIRMAR SAÍDA DO CLÃ ==========
class ConfirmarSaidaView(ui.View):
    def __init__(self, clan_id, guild_id, membro_id):
        super().__init__(timeout=30)
        self.clan_id = clan_id
        self.guild_id = guild_id
        self.membro_id = membro_id
    
    @ui.button(label="✅ Sim, sair do clã!", style=ButtonStyle.danger)
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.membro_id:
            await interaction.response.send_message("❌ Esta ação não é para você!", ephemeral=True)
            return
        
        guild = interaction.guild
        clans = carregar_clans(guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id == clan_data["dono_id"]:
            await interaction.response.send_message(
                "❌ O dono não pode sair do clã! Use o botão de excluir ou transfira a liderança.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        cargo = guild.get_role(clan_data["cargo_id"])
        if cargo:
            await interaction.user.remove_roles(cargo)
        
        if interaction.user.id in clan_data["membros"]:
            clan_data["membros"].remove(interaction.user.id)
        
        salvar_clans(guild.id, clans)
        
        for item in self.children:
            item.disabled = True
        self.children[0].label = "✅ Você saiu do clã!"
        
        await interaction.edit_original_response(view=self)
        
        await interaction.followup.send(
            f"✅ Você saiu do clã **{clan_data['nome']}**!",
            ephemeral=True
        )
        
        canais = clan_data.get("canais", {})
        texto_id = canais.get("texto_id")
        if texto_id:
            canal = guild.get_channel(texto_id)
            if canal:
                await canal.send(
                    f"👋 {interaction.user.mention} **saiu do clã**.\n"
                    f"📊 {len(clan_data['membros'])}/{clan_data['limite']} membros",
                    delete_after=30
                )
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()


# ========== PAINEL DO CLÃ ==========
class PainelClaView(ui.View):
    def __init__(self, cog, clan_id, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.clan_id = clan_id
        self.guild_id = guild_id
    
    @ui.button(label="📨 Convidar jogador", style=ButtonStyle.success, emoji="📨", custom_id="cla_convidar", row=0)
    async def convidar_membro(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id != clan_data["dono_id"]:
            await interaction.response.send_message("❌ Apenas o dono pode convidar!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) >= clan_data["limite"]:
            await interaction.response.send_message(f"❌ Limite atingido ({clan_data['limite']})!", ephemeral=True)
            return
        
        view = SelecionarMembroConviteView(self.clan_id, interaction.guild, clan_data["dono_id"], self.cog)
        
        embed = discord.Embed(
            title="📨 Convidar Jogador ao Clã",
            description=f"**Clã:** {clan_data['nome']}\n**Vagas:** {len(clan_data['membros'])}/{clan_data['limite']}\n\nSelecione o jogador para enviar o convite:",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="🚪 Sair do Clã", style=ButtonStyle.danger, emoji="🚪", custom_id="cla_sair", row=0)
    async def sair_cla(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id not in clan_data["membros"]:
            await interaction.response.send_message("❌ Você não pertence a este clã!", ephemeral=True)
            return
        
        if interaction.user.id == clan_data["dono_id"]:
            await interaction.response.send_message(
                "❌ Você é o dono do clã! Transfira a liderança ou exclua o clã.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🚪 Sair do Clã",
            description=(
                f"**Clã:** {clan_data['nome']}\n\n"
                "⚠️ Tem certeza que deseja sair do clã?\n\n"
                "Você perderá o acesso aos canais do clã."
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmarSaidaView(self.clan_id, interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="➖ Remover jogador", style=ButtonStyle.danger, emoji="➖", custom_id="cla_remove", row=1)
    async def remover_membro(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id != clan_data["dono_id"]:
            await interaction.response.send_message("❌ Apenas o dono pode remover!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) <= 1:
            await interaction.response.send_message("❌ Não há membros para remover!", ephemeral=True)
            return
        
        view = SelecionarMembroRemoveView(self.clan_id, interaction.guild, clan_data["dono_id"])
        
        embed = discord.Embed(
            title="➖ Remover Jogador do Clã",
            description=f"**Clã:** {clan_data['nome']}\n**Membros:** {len(clan_data['membros'])}\n\nSelecione o jogador abaixo:",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="👑 Gerenciar Limite", style=ButtonStyle.blurple, emoji="👑", custom_id="cla_limite", row=1)
    async def gerenciar_limite(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="👑 Gerenciar Limite",
            description=f"**Clã:** {clan_data['nome']}\n**Limite atual:** {clan_data['limite']} membros",
            color=discord.Color.gold()
        )
        
        view = GerenciarLimiteView(self.clan_id, clan_data['limite'])
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @ui.button(label="🗑️ Excluir Clã", style=ButtonStyle.danger, emoji="🗑️", custom_id="cla_excluir", row=1)
    async def excluir_cla(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚠️ CONFIRMAR EXCLUSÃO",
            description=(
                f"**Clã:** {clan_data['nome']}\n"
                f"**Dono:** <@{clan_data['dono_id']}>\n"
                f"**Membros:** {len(clan_data['membros'])}\n\n"
                "⚠️ **IRREVERSÍVEL!**\n\n"
                "• Todos os canais\n"
                "• A categoria\n"
                "• O cargo\n\n"
                "**Tem certeza?**"
            ),
            color=discord.Color.red()
        )
        
        view = ConfirmarExclusaoView(self.cog, self.clan_id, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ========== VIEW GERENCIAR LIMITE ==========
class GerenciarLimiteView(ui.View):
    def __init__(self, clan_id, limite_atual):
        super().__init__(timeout=60)
        self.clan_id = clan_id
        self.limite_atual = limite_atual
    
    @ui.button(label="➕ Aumentar", style=ButtonStyle.success, emoji="➕")
    async def aumentar(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        clan_data["limite"] += 1
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.followup.send(f"✅ Limite: **{clan_data['limite']}** membros!", ephemeral=True)
    
    @ui.button(label="➖ Diminuir", style=ButtonStyle.danger, emoji="➖")
    async def diminuir(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        if clan_data["limite"] <= len(clan_data["membros"]):
            await interaction.followup.send(f"❌ Clã tem {len(clan_data['membros'])} membros!", ephemeral=True)
            return
        
        if clan_data["limite"] <= 1:
            await interaction.followup.send("❌ Limite mínimo é 1!", ephemeral=True)
            return
        
        clan_data["limite"] -= 1
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.followup.send(f"✅ Limite: **{clan_data['limite']}** membros!", ephemeral=True)


# ========== PAINEL PRINCIPAL ==========
class PainelCriarClaView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @ui.button(label="Crie o seu CLÃ!", style=ButtonStyle.primary, emoji="⚔️", custom_id="criar_cla_btn")
    async def criar_cla(self, interaction: discord.Interaction, button: ui.Button):
        if tem_cla(interaction.user):
            await interaction.response.send_message("❌ Você já pertence a um clã!", ephemeral=True)
            return
        
        cog = self.bot.get_cog("ClansCog")
        modal = ModalNomeCla(cog)
        await interaction.response.send_modal(modal)


# ========== COG ==========
class ClansCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo de Clãs carregado!")
        
        self.bot.add_view(PainelCriarClaView(bot))
        asyncio.create_task(self.recarregar_paineis())
    
    async def recarregar_paineis(self):
        await self.bot.wait_until_ready()
        print("[CLÃ] 🔄 Recarregando painéis dos clãs...")
        
        for guild in self.bot.guilds:
            clans = carregar_clans(guild.id)
            print(f"[CLÃ]    Servidor: {guild.name} - {len(clans)} clãs encontrados")
            
            for clan_id, clan_data in clans.items():
                canais = clan_data.get("canais", {})
                texto_id = canais.get("texto_id")
                
                if texto_id:
                    canal = guild.get_channel(texto_id)
                    if canal:
                        view = PainelClaView(self, clan_id, guild.id)
                        self.bot.add_view(view)
                        print(f"[CLÃ]    ✅ Painel recarregado: {clan_data['nome']}")
                    else:
                        print(f"[CLÃ]    ⚠️ Canal não encontrado para: {clan_data['nome']}")
                else:
                    print(f"[CLÃ]    ⚠️ Clan sem canal de texto: {clan_data['nome']}")
        
        print("[CLÃ] ✅ Recarregamento concluído!")
    
    async def criar_canais_cla(self, interaction, user, nome_cla, cargo_cla, nome_texto, nome_voz1, nome_voz2):
        try:
            guild = interaction.guild
            
            categoria_base = guild.get_channel(CATEGORIA_BASE_ID)
            if not categoria_base or not isinstance(categoria_base, discord.CategoryChannel):
                await interaction.followup.send("❌ Categoria base não encontrada!", ephemeral=True)
                return
            
            nome_categoria = f"・ {nome_cla}"
            
            overwrites_categoria = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False, speak=False),
                cargo_cla: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True, read_message_history=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, connect=True)
            }
            
            # Adicionar ADMs e cargo máximo
            try:
                from modules.adm_system import load_adm_roles, load_cargo_max
                
                adm_roles = load_adm_roles(guild.id)
                for role_name in adm_roles:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        overwrites_categoria[role] = discord.PermissionOverwrite(
                            read_messages=True, send_messages=True, connect=True, speak=True
                        )
                
                cargo_max_nome = load_cargo_max(guild.id)
                cargo_max = discord.utils.get(guild.roles, name=cargo_max_nome)
                if cargo_max:
                    overwrites_categoria[cargo_max] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, connect=True, speak=True
                    )
            except:
                pass
            
            categoria_cla = await guild.create_category(
                name=nome_categoria,
                overwrites=overwrites_categoria,
                reason=f"Categoria do clã {nome_cla}"
            )
            
            nova_posicao = categoria_base.position + 1
            await categoria_cla.edit(position=nova_posicao)
            
            overwrites_canais = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False, speak=False),
                cargo_cla: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, connect=True)
            }
            
            # Adicionar ADMs e cargo máximo aos canais também
            try:
                from modules.adm_system import load_adm_roles, load_cargo_max
                
                adm_roles = load_adm_roles(guild.id)
                for role_name in adm_roles:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        overwrites_canais[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                
                cargo_max_nome = load_cargo_max(guild.id)
                cargo_max = discord.utils.get(guild.roles, name=cargo_max_nome)
                if cargo_max:
                    overwrites_canais[cargo_max] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            except:
                pass
            
            canal_texto = await guild.create_text_channel(
                name=nome_texto,
                category=categoria_cla,
                overwrites=overwrites_canais,
                topic=f"Clã: {nome_cla} | Dono: {user.name}"
            )
            
            canal_voz1 = await guild.create_voice_channel(
                name=nome_voz1,
                category=categoria_cla,
                overwrites=overwrites_canais
            )
            
            canal_voz2 = await guild.create_voice_channel(
                name=nome_voz2,
                category=categoria_cla,
                overwrites=overwrites_canais
            )
            
            clans = carregar_clans(guild.id)
            clan_id = None
            for cid, cdata in clans.items():
                if cdata.get("cargo_id") == cargo_cla.id:
                    clan_id = cid
                    break
            
            if clan_id:
                clans[clan_id]["canais"] = {
                    "texto_id": canal_texto.id,
                    "voz1_id": canal_voz1.id,
                    "voz2_id": canal_voz2.id
                }
                clans[clan_id]["categoria_id"] = categoria_cla.id
                salvar_clans(guild.id, clans)
            
            embed = discord.Embed(
                title=f"{EMOJI_CLANS} ADICIONAR MEMBROS AO CLÃ",
                description=(
                    f"**Clã:** {nome_cla}\n"
                    f"**Dono:** {user.mention}\n\n"
                    "Para adicionar novos jogadores ao seu clã, clique no botão abaixo.\n\n"
                    f"✅ Limite gratuito: **{LIMITE_PADRAO} membros**.\n\n"
                    "💎 Para aumentar o limite, veja **#💎・𝐕𝐈𝐏𝐬**."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Criado em: {datetime.now().strftime('%d/%m/%Y')}")
            
            view = PainelClaView(self, clan_id if clan_id else str(user.id), guild.id)
            await canal_texto.send(f"{EMOJI_CLANS} **Bem-vindos ao clã {nome_cla}** {EMOJI_CLANS}", embed=embed, view=view)
            
            self.bot.add_view(view)
            
            await interaction.followup.send(
                f"✅ **Clã criado!**\n\n"
                f"📁 Categoria: {categoria_cla.name}\n"
                f"📝 {canal_texto.mention}\n"
                f"🎙️ {canal_voz1.mention}\n"
                f"🎙️ {canal_voz2.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"[CLÃ] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Erro: {str(e)[:200]}", ephemeral=True)
            except:
                pass
    
    async def excluir_cla(self, interaction, clan_id):
        try:
            guild = interaction.guild
            clans = carregar_clans(guild.id)
            clan_data = clans.get(clan_id)
            
            if not clan_data:
                await interaction.followup.send("❌ Clã não encontrado!", ephemeral=True)
                return
            
            canais = clan_data.get("canais", {})
            for chave in ["texto_id", "voz1_id", "voz2_id"]:
                canal_id = canais.get(chave)
                if canal_id:
                    canal = guild.get_channel(canal_id)
                    if canal:
                        await canal.delete()
            
            categoria_id = clan_data.get("categoria_id")
            if categoria_id:
                categoria = guild.get_channel(categoria_id)
                if categoria:
                    await categoria.delete()
            
            cargo_id = clan_data.get("cargo_id")
            if cargo_id:
                cargo = guild.get_role(cargo_id)
                if cargo:
                    await cargo.delete()
            
            del clans[clan_id]
            salvar_clans(guild.id, clans)
            
            await interaction.followup.send(f"✅ Clã **{clan_data['nome']}** excluído!", ephemeral=True)
            
        except Exception as e:
            print(f"[CLÃ] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Erro: {str(e)[:200]}", ephemeral=True)
            except:
                pass
    
    @commands.command(name="setup_clans")
    @commands.has_permissions(administrator=True)
    async def setup_clans(self, ctx):
        embed = discord.Embed(
            title=f"{EMOJI_CLANS} CRIE SEU CLÃ {EMOJI_CLANS}",
            description=(
                "Reúna seus amigos e tenha seu próprio espaço no Discord!\n\n"
                "✅ **Totalmente gratuito.**\n\n"
                "Ao criar um clã, você recebe:\n\n"
                "💬 **1 canal de texto exclusivo.**\n"
                "🎙️ **2 canais de voz exclusivos.**\n\n"
                "Um lugar para conversar, organizar suas aventuras e jogar com sua equipe.\n\n"
                "💎 Precisa de mais canais ou benefícios extras? Confira as opções disponíveis em **#💎・𝐕𝐈𝐏𝐬**.\n\n"
                "🤝 Monte seu clã e comece sua jornada no ReyCraft HC!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="ReyCraft HC • Sistema de Clãs")
        
        view = PainelCriarClaView(self.bot)
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        
        print(f"✅ Painel de clãs configurado em #{ctx.channel.name}")

# ========== ATUALIZAR PAINEL DE KILLS ==========

async def atualizar_painel_kills(bot, guild_id, clan_id):
    """Atualiza a linha de Kills no painel do clã já existente no Discord."""
    clans = carregar_clans(guild_id)
    clan_data = clans.get(clan_id)
    if not clan_data:
        return

    canais = clan_data.get("canais", {})
    texto_id = canais.get("texto_id")
    msg_id = canais.get("mensagem_painel_id")
    if not texto_id or not msg_id:
        return  # clã criado antes dessa atualização, ainda não tem o ID salvo

    guild = bot.get_guild(guild_id)
    if not guild:
        return
    canal = guild.get_channel(texto_id)
    if not canal:
        return

    try:
        mensagem = await canal.fetch_message(msg_id)
    except Exception:
        return

    if not mensagem.embeds:
        return

    embed = mensagem.embeds[0]
    kills = clan_data.get("kills", 0)
    mortes = clan_data.get("mortes", 0)

    encontrado = False
    for i, campo in enumerate(embed.fields):
        if campo.name == "🗡️ Kills do Clã":
            embed.set_field_at(i, name="🗡️ Kills do Clã", value=f"{kills} kills / {mortes} mortes", inline=False)
            encontrado = True
            break
    if not encontrado:
        embed.add_field(name="🗡️ Kills do Clã", value=f"{kills} kills / {mortes} mortes", inline=False)

    try:
        await mensagem.edit(embed=embed)
    except Exception as e:
        print(f"[CLÃ] ⚠️ Não consegui atualizar o painel de {clan_data['nome']}: {e}")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(ClansCog(bot))
    print("✅ Sistema de Clãs configurado!")
