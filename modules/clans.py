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
from utils.memory import load_all_data, save_all_data, load_guild_data, save_guild_data

# ========== CONFIGURAÇÕES ==========
# ID do canal onde o painel principal será postado
CANAL_PAINEL_ID = 1516443229770350623  # ← COLOQUE O ID DO CANAL AQUI

# ID do cargo base para copiar permissões
CARGO_BASE_ID = 1516456654063931432

# ID do canal onde os canais do clã serão criados abaixo
CANAL_BASE_CLANS_ID = 1516443229770350623

# Limite padrão de membros
LIMITE_PADRAO = 8

# ========== FUNÇÕES DE MEMÓRIA ==========
def carregar_clans(guild_id):
    """Carrega todos os clãs de um servidor"""
    return load_guild_data(guild_id, "clans", {})

def salvar_clans(guild_id, clans):
    """Salva todos os clãs de um servidor"""
    save_guild_data(guild_id, "clans", clans)

def tem_cla(member: discord.Member) -> bool:
    """Verifica se um membro já tem um cargo de clã"""
    clans = carregar_clans(member.guild.id)
    
    for clan_id, clan_data in clans.items():
        cargo_id = clan_data.get("cargo_id")
        if cargo_id:
            role = member.guild.get_role(cargo_id)
            if role and role in member.roles:
                return True
    return False

def get_cla_do_membro(member: discord.Member):
    """Retorna os dados do clã que o membro pertence"""
    clans = carregar_clans(member.guild.id)
    
    for clan_id, clan_data in clans.items():
        cargo_id = clan_data.get("cargo_id")
        if cargo_id:
            role = member.guild.get_role(cargo_id)
            if role and role in member.roles:
                return clan_id, clan_data
    return None, None

def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro é staff"""
    try:
        from modules.adm_system import is_staff as adm_is_staff
        return adm_is_staff(member)
    except:
        return member.guild_permissions.administrator

# ========== MODAL PARA NOME DO CLÃ ==========
class ModalNomeCla(ui.Modal, title="⚔️ Criar Clã"):
    nome_cla = ui.TextInput(
        label="Nome do seu clã:",
        placeholder="Ex: Dragões de Fogo, Guerreiros da Noite...",
        required=True,
        max_length=50,
        min_length=3
    )
    
    def __init__(self, cog, guild):
        super().__init__()
        self.cog = cog
        self.guild = guild
    
    async def on_submit(self, interaction: discord.Interaction):
        nome = self.nome_cla.value.strip()
        
        # Verificar se já tem clã
        if tem_cla(interaction.user):
            await interaction.response.send_message(
                "❌ Você já pertence a um clã! Saia do seu clã atual antes de criar outro.",
                ephemeral=True
            )
            return
        
        # Verificar se nome já existe
        clans = carregar_clans(interaction.guild.id)
        for clan_data in clans.values():
            if clan_data["nome"].lower() == nome.lower():
                await interaction.response.send_message(
                    f"❌ Já existe um clã com o nome `{nome}`! Escolha outro nome.",
                    ephemeral=True
                )
                return
        
        # Verificar se já tem cargo de clã
        for role in interaction.user.roles:
            if role.name.startswith("⚔️ "):
                await interaction.response.send_message(
                    "❌ Você já tem um cargo de clã! Remova-o antes de criar outro.",
                    ephemeral=True
                )
                return
        
        await interaction.response.defer(ephemeral=True)
        
        # Criar cargo do clã
        cargo_base = interaction.guild.get_role(CARGO_BASE_ID)
        if not cargo_base:
            await interaction.followup.send("❌ Cargo base não encontrado! Contate um administrador.", ephemeral=True)
            return
        
        try:
            # Criar cargo com as mesmas permissões do cargo base
            cargo_cla = await interaction.guild.create_role(
                name=f"⚔️ {nome}",
                permissions=cargo_base.permissions,
                color=discord.Color.from_rgb(88, 101, 242),
                hoist=True,
                mentionable=True,
                reason=f"Clã criado por {interaction.user.name}"
            )
            
            # Dar o cargo para o criador
            await interaction.user.add_roles(cargo_cla)
            
            # Salvar dados do clã
            clan_id = str(interaction.user.id)
            clans[clan_id] = {
                "nome": nome,
                "cargo_id": cargo_cla.id,
                "dono_id": interaction.user.id,
                "limite": LIMITE_PADRAO,
                "membros": [interaction.user.id],
                "canais": {},
                "criado_em": datetime.now().isoformat()
            }
            salvar_clans(interaction.guild.id, clans)
            
            # ✅ CORRIGIDO: Enviar mensagem com botão para abrir o próximo modal
            embed = discord.Embed(
                title="✅ Clã criado com sucesso!",
                description=f"Seu clã **{nome}** foi criado com sucesso!\n"
                           f"Cargo: {cargo_cla.mention}\n\n"
                           f"**Próximo passo:** Configure o nome do seu canal de texto.",
                color=discord.Color.green()
            )
            
            # Botão para abrir o modal do canal de texto
            view = BotaoCanalTextoView(self.cog, nome, cargo_cla)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Erro ao criar clã: {e}")
            await interaction.followup.send(f"❌ Erro ao criar clã: {str(e)[:100]}", ephemeral=True)


# ========== VIEW COM BOTÃO PARA ABRIR MODAL DO CANAL DE TEXTO ==========
class BotaoCanalTextoView(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
    
    @ui.button(label="📝 Nomear Canal de Texto", style=ButtonStyle.primary, emoji="📝")
    async def abrir_modal_texto(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalTexto(self.cog, self.nome_cla, self.cargo_cla)
        await interaction.response.send_modal(modal)


# ========== MODAL PARA CANAL DE TEXTO ==========
class ModalCanalTexto(ui.Modal, title="📝 Nome do Canal de Texto"):
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
        
        # Salvar nome do canal de texto temporariamente
        clans = carregar_clans(interaction.guild.id)
        
        # Encontrar o clã pelo cargo
        clan_id = None
        for cid, cdata in clans.items():
            if cdata["cargo_id"] == self.cargo_cla.id:
                clan_id = cid
                break
        
        if clan_id and clan_id in clans:
            clans[clan_id]["canais"]["texto_nome"] = nome_texto
            salvar_clans(interaction.guild.id, clans)
        
        # Enviar botão para próximo modal
        embed = discord.Embed(
            title="🎙️ Configurar Canal de Voz 1",
            description=f"Canal de texto definido: **{nome_texto}**\n\n"
                       f"Agora escolha o nome do **primeiro canal de voz**:",
            color=discord.Color.blue()
        )
        
        view = BotaoCanalVoz1View(self.cog, self.nome_cla, self.cargo_cla, nome_texto)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ========== VIEW COM BOTÃO PARA CANAL DE VOZ 1 ==========
class BotaoCanalVoz1View(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
    
    @ui.button(label="🎙️ Nomear Canal de Voz 1", style=ButtonStyle.primary, emoji="🎙️")
    async def abrir_modal_voz1(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalVoz1(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto)
        await interaction.response.send_modal(modal)


# ========== MODAL PARA CANAL DE VOZ 1 ==========
class ModalCanalVoz1(ui.Modal, title="🎙️ Nome do Canal de Voz 1"):
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
        
        # Salvar nome do canal de voz 1
        clans = carregar_clans(interaction.guild.id)
        
        clan_id = None
        for cid, cdata in clans.items():
            if cdata["cargo_id"] == self.cargo_cla.id:
                clan_id = cid
                break
        
        if clan_id and clan_id in clans:
            clans[clan_id]["canais"]["voz1_nome"] = nome_voz1
            salvar_clans(interaction.guild.id, clans)
        
        # Botão para último modal
        embed = discord.Embed(
            title="🎙️ Configurar Canal de Voz 2",
            description=f"Canal de texto: **{self.nome_texto}**\n"
                       f"Canal de voz 1: **{nome_voz1}**\n\n"
                       f"Agora escolha o nome do **segundo canal de voz**:",
            color=discord.Color.blue()
        )
        
        view = BotaoCanalVoz2View(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto, nome_voz1)
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ========== VIEW COM BOTÃO PARA CANAL DE VOZ 2 ==========
class BotaoCanalVoz2View(ui.View):
    def __init__(self, cog, nome_cla, cargo_cla, nome_texto, nome_voz1):
        super().__init__(timeout=300)
        self.cog = cog
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
        self.nome_voz1 = nome_voz1
    
    @ui.button(label="🎙️ Nomear Canal de Voz 2", style=ButtonStyle.primary, emoji="🎙️")
    async def abrir_modal_voz2(self, interaction: discord.Interaction, button: ui.Button):
        modal = ModalCanalVoz2(self.cog, self.nome_cla, self.cargo_cla, self.nome_texto, self.nome_voz1)
        await interaction.response.send_modal(modal)


# ========== MODAL PARA CANAL DE VOZ 2 ==========
class ModalCanalVoz2(ui.Modal, title="🎙️ Nome do Canal de Voz 2"):
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
        
        # Criar todos os canais agora
        await self.cog.criar_canais_cla(
            interaction,
            interaction.user,
            self.nome_cla,
            self.cargo_cla,
            self.nome_texto,
            self.nome_voz1,
            nome_voz2
        )

# ========== VIEWS PARA BOTÕES DOS MODAIS ==========
class CriarCanaisView(ui.View):
    def __init__(self, cog, user, nome_cla, cargo_cla):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
    
    @ui.button(label="📝 Nomear Canais", style=ButtonStyle.primary, emoji="📝")
    async def nomear_canais(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Apenas quem criou o clã pode fazer isso!", ephemeral=True)
            return
        
        modal = ModalCanalTexto(self.cog, self.user, self.nome_cla, self.cargo_cla)
        await interaction.response.send_modal(modal)

class CriarCanalVoz1View(ui.View):
    def __init__(self, cog, user, nome_cla, cargo_cla, nome_texto):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
    
    @ui.button(label="🎙️ Nomear Voz 1", style=ButtonStyle.primary, emoji="🎙️")
    async def nomear_voz1(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Apenas quem criou o clã pode fazer isso!", ephemeral=True)
            return
        
        modal = ModalCanalVoz1(self.cog, self.user, self.nome_cla, self.cargo_cla, self.nome_texto)
        await interaction.response.send_modal(modal)

class CriarCanalVoz2View(ui.View):
    def __init__(self, cog, user, nome_cla, cargo_cla, nome_texto, nome_voz1):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user
        self.nome_cla = nome_cla
        self.cargo_cla = cargo_cla
        self.nome_texto = nome_texto
        self.nome_voz1 = nome_voz1
    
    @ui.button(label="🎙️ Nomear Voz 2", style=ButtonStyle.primary, emoji="🎙️")
    async def nomear_voz2(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Apenas quem criou o clã pode fazer isso!", ephemeral=True)
            return
        
        modal = ModalCanalVoz2(self.cog, self.user, self.nome_cla, self.cargo_cla, self.nome_texto, self.nome_voz1)
        await interaction.response.send_modal(modal)

# ========== VIEW DO PAINEL DO CLÃ (CANAL DE TEXTO) ==========
class PainelClaView(ui.View):
    def __init__(self, cog, clan_id, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.clan_id = clan_id
        self.guild_id = guild_id
    
    @ui.button(label="➕ Adicionar um jogador ao seu clã!", style=ButtonStyle.success, emoji="➕", custom_id="add_membro_cla", row=0)
    async def adicionar_membro(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        # Verificar se é o dono
        if interaction.user.id != clan_data["dono_id"]:
            await interaction.response.send_message("❌ Apenas o dono do clã pode adicionar membros!", ephemeral=True)
            return
        
        # Verificar limite
        if len(clan_data["membros"]) >= clan_data["limite"]:
            await interaction.response.send_message(
                f"❌ Limite de membros atingido ({clan_data['limite']}/{clan_data['limite']})!\n"
                f"💎 Para aumentar o limite, adquira VIP em #💎・𝐕𝐈𝐏𝐬.",
                ephemeral=True
            )
            return
        
        # Criar modal para selecionar membro
        modal = ModalAdicionarMembro(self.cog, self.clan_id)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➖ Remover um jogador do seu clã!", style=ButtonStyle.danger, emoji="➖", custom_id="remove_membro_cla", row=0)
    async def remover_membro(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id != clan_data["dono_id"]:
            await interaction.response.send_message("❌ Apenas o dono do clã pode remover membros!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) <= 1:
            await interaction.response.send_message("❌ Não há membros para remover!", ephemeral=True)
            return
        
        # Mostrar select menu com membros
        view = RemoverMembroView(self.cog, self.clan_id, interaction.guild)
        await interaction.response.send_message("Selecione o membro para remover:", view=view, ephemeral=True)
    
    @ui.button(label="👑 Gerenciar Limite", style=ButtonStyle.blurple, emoji="👑", custom_id="gerenciar_limite_cla", row=1)
    async def gerenciar_limite(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode gerenciar limites!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        limite_atual = clan_data["limite"]
        
        embed = discord.Embed(
            title="👑 Gerenciar Limite do Clã",
            description=f"**Clã:** {clan_data['nome']}\n**Limite atual:** {limite_atual} membros\n\nEscolha uma ação:",
            color=discord.Color.gold()
        )
        
        view = GerenciarLimiteView(self.cog, self.clan_id, limite_atual)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ========== MODAL PARA ADICIONAR MEMBRO ==========
class ModalAdicionarMembro(ui.Modal, title="➕ Adicionar Membro"):
    usuario_id = ui.TextInput(
        label="ID do usuário:",
        placeholder="Cole o ID do usuário aqui...",
        required=True,
        max_length=20
    )
    
    def __init__(self, cog, clan_id):
        super().__init__()
        self.cog = cog
        self.clan_id = clan_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.usuario_id.value.strip())
        except:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
            return
        
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Usuário não encontrado no servidor!", ephemeral=True)
            return
        
        # Verificar se já tem clã
        if tem_cla(member):
            await interaction.response.send_message("❌ Este usuário já pertence a um clã!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        # Adicionar membro
        cargo = interaction.guild.get_role(clan_data["cargo_id"])
        if cargo:
            await member.add_roles(cargo)
        
        clan_data["membros"].append(member.id)
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.response.send_message(
            f"✅ {member.mention} foi adicionado ao clã **{clan_data['nome']}**!\n"
            f"📊 Membros: {len(clan_data['membros'])}/{clan_data['limite']}",
            ephemeral=True
        )

# ========== VIEW PARA REMOVER MEMBRO ==========
class RemoverMembroView(ui.View):
    def __init__(self, cog, clan_id, guild):
        super().__init__(timeout=60)
        self.cog = cog
        self.clan_id = clan_id
        self.guild = guild
        
        clans = carregar_clans(guild.id)
        clan_data = clans.get(clan_id)
        
        if clan_data:
            self.select_menu = ui.Select(
                placeholder="Selecione o membro para remover...",
                min_values=1,
                max_values=1
            )
            
            for membro_id in clan_data["membros"]:
                if membro_id != clan_data["dono_id"]:  # Não pode remover o dono
                    member = guild.get_member(membro_id)
                    if member:
                        self.select_menu.add_option(
                            label=member.display_name[:100],
                            value=str(member.id),
                            description=f"ID: {member.id}"
                        )
            
            self.select_menu.callback = self.remover_callback
            self.add_item(self.select_menu)
    
    async def remover_callback(self, interaction: discord.Interaction):
        membro_id = int(self.select_menu.values[0])
        member = self.guild.get_member(membro_id)
        
        if not member:
            await interaction.response.send_message("❌ Membro não encontrado!", ephemeral=True)
            return
        
        clans = carregar_clans(self.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        # Remover cargo
        cargo = self.guild.get_role(clan_data["cargo_id"])
        if cargo:
            await member.remove_roles(cargo)
        
        # Remover da lista
        clan_data["membros"].remove(membro_id)
        salvar_clans(self.guild.id, clans)
        
        await interaction.response.send_message(
            f"✅ {member.mention} foi removido do clã **{clan_data['nome']}**!\n"
            f"📊 Membros: {len(clan_data['membros'])}/{clan_data['limite']}",
            ephemeral=True
        )

# ========== VIEW PARA GERENCIAR LIMITE (STAFF) ==========
class GerenciarLimiteView(ui.View):
    def __init__(self, cog, clan_id, limite_atual):
        super().__init__(timeout=60)
        self.cog = cog
        self.clan_id = clan_id
        self.limite_atual = limite_atual
    
    @ui.button(label="➕ Aumentar Limite", style=ButtonStyle.success, emoji="➕")
    async def aumentar_limite(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        clan_data["limite"] += 1
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.response.send_message(
            f"✅ Limite aumentado para **{clan_data['limite']}** membros!",
            ephemeral=True
        )
    
    @ui.button(label="➖ Diminuir Limite", style=ButtonStyle.danger, emoji="➖")
    async def diminuir_limite(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if clan_data["limite"] <= len(clan_data["membros"]):
            await interaction.response.send_message(
                f"❌ Não é possível diminuir! O clã tem {len(clan_data['membros'])} membros.",
                ephemeral=True
            )
            return
        
        if clan_data["limite"] <= 1:
            await interaction.response.send_message("❌ Limite mínimo é 1!", ephemeral=True)
            return
        
        clan_data["limite"] -= 1
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.response.send_message(
            f"✅ Limite diminuído para **{clan_data['limite']}** membros!",
            ephemeral=True
        )

# ========== VIEW DO PAINEL PRINCIPAL ==========
class PainelCriarClaView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="Crie o seu CLÃ!", style=ButtonStyle.primary, emoji="⚔️", custom_id="criar_cla")
    async def criar_cla(self, interaction: discord.Interaction, button: ui.Button):
        # Verificar se já tem clã
        if tem_cla(interaction.user):
            await interaction.response.send_message(
                "❌ Você já pertence a um clã! Saia do seu clã atual antes de criar outro.",
                ephemeral=True
            )
            return
        
        # Verificar se já tem cargo de clã
        for role in interaction.user.roles:
            if role.name.startswith("⚔️ "):
                await interaction.response.send_message(
                    "❌ Você já tem um cargo de clã! Remova-o antes de criar outro.",
                    ephemeral=True
                )
                return
        
        modal = ModalNomeCla(None, interaction.guild)
        await interaction.response.send_modal(modal)

# ========== COG PRINCIPAL ==========
class ClansCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo de Clãs carregado!")
    
    async def criar_canais_cla(self, interaction, user, nome_cla, cargo_cla, nome_texto, nome_voz1, nome_voz2):
        """Cria todos os canais do clã"""
        try:
            guild = interaction.guild
            
            # Encontrar o canal base
            canal_base = guild.get_channel(CANAL_BASE_CLANS_ID)
            if not canal_base:
                await interaction.followup.send("❌ Canal base não encontrado!", ephemeral=True)
                return
            
            categoria = canal_base.category
            
            # Permissões dos canais
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                cargo_cla: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            # Criar canal de texto
            canal_texto = await guild.create_text_channel(
                name=nome_texto,
                category=categoria,
                overwrites=overwrites,
                topic=f"Clã: {nome_cla} | Dono: {user.name}",
                reason=f"Canal do clã {nome_cla}"
            )
            
            # Criar canais de voz
            canal_voz1 = await guild.create_voice_channel(
                name=nome_voz1,
                category=categoria,
                overwrites=overwrites,
                reason=f"Canal de voz 1 do clã {nome_cla}"
            )
            
            canal_voz2 = await guild.create_voice_channel(
                name=nome_voz2,
                category=categoria,
                overwrites=overwrites,
                reason=f"Canal de voz 2 do clã {nome_cla}"
            )
            
            # Salvar IDs dos canais
            clans = carregar_clans(guild.id)
            clan_id = str(user.id)
            
            if clan_id in clans:
                clans[clan_id]["canais"] = {
                    "texto_id": canal_texto.id,
                    "voz1_id": canal_voz1.id,
                    "voz2_id": canal_voz2.id
                }
                salvar_clans(guild.id, clans)
            
            # Enviar painel no canal de texto
            embed = discord.Embed(
                title="👥 ADICIONAR MEMBROS AO CLÃ",
                description=(
                    f"**Clã:** {nome_cla}\n"
                    f"**Dono:** {user.mention}\n\n"
                    "Para adicionar novos jogadores ao seu clã, clique no botão **\"Adicionar um jogador ao seu clã!\"** "
                    "e cole o ID do jogador que deseja convidar.\n\n"
                    f"✅ Todo clã possui gratuitamente espaço para até **{LIMITE_PADRAO} membros**.\n\n"
                    "💎 Caso deseje aumentar o limite de jogadores do seu clã, consulte as opções disponíveis em **#💎・𝐕𝐈𝐏𝐬**."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Clã criado em: {datetime.now().strftime('%d/%m/%Y')}")
            
            view = PainelClaView(self, clan_id, guild.id)
            
            await canal_texto.send(f"⚔️ **Bem-vindos ao clã {nome_cla}** ⚔️", embed=embed, view=view)
            
            await interaction.followup.send(
                f"✅ Canais do clã **{nome_cla}** criados com sucesso!\n"
                f"📝 Texto: {canal_texto.mention}\n"
                f"🎙️ Voz 1: {canal_voz1.mention}\n"
                f"🎙️ Voz 2: {canal_voz2.mention}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"❌ Erro ao criar canais do clã: {e}")
            await interaction.followup.send(f"❌ Erro ao criar canais: {str(e)[:100]}", ephemeral=True)
    
    @commands.command(name="setup_clans")
    @commands.has_permissions(administrator=True)
    async def setup_clans(self, ctx):
        """Configura o painel de criação de clãs"""
        
        embed = discord.Embed(
            title="⚔️ CRIE SEU CLÃ ⚔️",
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
        
        view = PainelCriarClaView()
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        
        print(f"✅ Painel de clãs configurado em #{ctx.channel.name}")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(ClansCog(bot))
    bot.add_view(PainelCriarClaView())
    print("✅ Sistema de Clãs configurado!")
