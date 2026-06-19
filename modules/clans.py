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
CANAL_BASE_CLANS_ID = 1516443229770350623
CATEGORIA_BASE_ID = 1517656643494477835  # ID da categoria base para copiar permissões
LIMITE_PADRAO = 8

# ========== FUNÇÕES AUXILIARES ==========
def carregar_clans(guild_id):
    """Carrega todos os clãs do servidor"""
    return load_guild_data(guild_id, "clans", {})

def salvar_clans(guild_id, clans):
    """Salva todos os clãs do servidor"""
    save_guild_data(guild_id, "clans", clans)

def tem_cla(member: discord.Member) -> bool:
    """Verifica se um membro já tem cargo de clã"""
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
        if role.name.startswith("⚔️ "):
            return True
    
    return False

def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro é staff"""
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
        
        # Verificações
        if tem_cla(interaction.user):
            await interaction.response.send_message("❌ Você já pertence a um clã!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        for clan_data in clans.values():
            if clan_data["nome"].lower() == nome.lower():
                await interaction.response.send_message(f"❌ Já existe um clã com o nome `{nome}`!", ephemeral=True)
                return
        
        await interaction.response.defer(ephemeral=True)
        
        # Criar cargo
        cargo_base = interaction.guild.get_role(CARGO_BASE_ID)
        if not cargo_base:
            await interaction.followup.send("❌ Cargo base não encontrado!", ephemeral=True)
            return
        
        try:
            cargo_cla = await interaction.guild.create_role(
                name=f"⚔️ {nome}",
                permissions=cargo_base.permissions,
                color=discord.Color.from_rgb(88, 101, 242),
                hoist=True,
                mentionable=True,
                reason=f"Clã criado por {interaction.user.name}"
            )
            
            await interaction.user.add_roles(cargo_cla)
            
            # Salvar
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
            
            # Próximo passo
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
        
        # Salvar
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
        
        # Salvar
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
            await interaction.followup.send("❌ Erro interno! Cog não encontrado.", ephemeral=True)
            return
        
        # Chamar a função de criar canais
        await self.cog.criar_canais_cla(
            interaction=interaction,
            user=interaction.user,
            nome_cla=self.nome_cla,
            cargo_cla=self.cargo_cla,
            nome_texto=self.nome_texto,
            nome_voz1=self.nome_voz1,
            nome_voz2=nome_voz2
        )

# ========== VIEW DE CONFIRMAÇÃO DE EXCLUSÃO ==========
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

# ========== PAINEL DO CLÃ ==========
class PainelClaView(ui.View):
    def __init__(self, cog, clan_id, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.clan_id = clan_id
        self.guild_id = guild_id
    
    @ui.button(label="➕ Adicionar jogador ao clã!", style=ButtonStyle.success, emoji="➕", custom_id="cla_add_membro", row=0)
    async def adicionar_membro(self, interaction: discord.Interaction, button: ui.Button):
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        if interaction.user.id != clan_data["dono_id"]:
            await interaction.response.send_message("❌ Apenas o dono pode adicionar!", ephemeral=True)
            return
        
        if len(clan_data["membros"]) >= clan_data["limite"]:
            await interaction.response.send_message(f"❌ Limite atingido ({clan_data['limite']})!", ephemeral=True)
            return
        
        modal = ModalAdicionarMembro(self.clan_id)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➖ Remover jogador do clã!", style=ButtonStyle.danger, emoji="➖", custom_id="cla_remove_membro", row=0)
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
        
        view = RemoverMembroView(self.clan_id, interaction.guild)
        await interaction.response.send_message("Selecione o membro:", view=view, ephemeral=True)
    
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
        # Apenas staff pode ver e usar este botão
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode excluir clãs!", ephemeral=True)
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
                "⚠️ **Esta ação é IRREVERSÍVEL!**\n\n"
                "Serão excluídos:\n"
                "• Todos os canais do clã\n"
                "• A categoria do clã\n"
                "• O cargo do clã\n\n"
                "**Tem certeza?**"
            ),
            color=discord.Color.red()
        )
        
        view = ConfirmarExclusaoView(self.cog, self.clan_id, interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ========== MODAL ADICIONAR MEMBRO ==========
class ModalAdicionarMembro(ui.Modal, title="➕ Adicionar Membro"):
    usuario_id = ui.TextInput(
        label="ID do usuário:",
        placeholder="Cole o ID aqui...",
        required=True,
        max_length=20
    )
    
    def __init__(self, clan_id):
        super().__init__()
        self.clan_id = clan_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = int(self.usuario_id.value.strip())
        except:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
            return
        
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ Usuário não encontrado!", ephemeral=True)
            return
        
        if tem_cla(member):
            await interaction.response.send_message("❌ Esse usuário já pertence a um clã!", ephemeral=True)
            return
        
        clans = carregar_clans(interaction.guild.id)
        clan_data = clans.get(self.clan_id)
        
        if not clan_data:
            await interaction.response.send_message("❌ Clã não encontrado!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        cargo = interaction.guild.get_role(clan_data["cargo_id"])
        if cargo:
            await member.add_roles(cargo)
        
        clan_data["membros"].append(member.id)
        salvar_clans(interaction.guild.id, clans)
        
        await interaction.followup.send(
            f"✅ {member.mention} adicionado ao clã **{clan_data['nome']}**!\n"
            f"📊 {len(clan_data['membros'])}/{clan_data['limite']}",
            ephemeral=True
        )

# ========== VIEW REMOVER MEMBRO ==========
class RemoverMembroView(ui.View):
    def __init__(self, clan_id, guild):
        super().__init__(timeout=60)
        self.clan_id = clan_id
        self.guild = guild
        
        clans = carregar_clans(guild.id)
        clan_data = clans.get(clan_id)
        
        if clan_data:
            select = ui.Select(placeholder="Selecione o membro...", min_values=1, max_values=1)
            
            for membro_id in clan_data["membros"]:
                if membro_id != clan_data["dono_id"]:
                    member = guild.get_member(membro_id)
                    if member:
                        select.add_option(label=member.display_name[:100], value=str(member.id), description=f"ID: {member.id}")
            
            if len(select.options) > 0:
                select.callback = self.remover_callback
                self.add_item(select)
    
    async def remover_callback(self, interaction: discord.Interaction):
        membro_id = int(self.children[0].values[0])
        member = self.guild.get_member(membro_id)
        
        if not member:
            await interaction.response.send_message("❌ Membro não encontrado!", ephemeral=True)
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
        
        await interaction.followup.send(
            f"✅ {member.mention} removido do clã **{clan_data['nome']}**!\n"
            f"📊 {len(clan_data['membros'])}/{clan_data['limite']}",
            ephemeral=True
        )

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
    
    async def criar_canais_cla(self, interaction, user, nome_cla, cargo_cla, nome_texto, nome_voz1, nome_voz2):
        """Cria todos os canais do clã com categoria própria"""
        try:
            guild = interaction.guild
            
            print(f"\n[CLÃ] ========== INICIANDO CRIAÇÃO ==========")
            print(f"[CLÃ] Clã: {nome_cla}")
            print(f"[CLÃ] Texto: {nome_texto}")
            print(f"[CLÃ] Voz 1: {nome_voz1}")
            print(f"[CLÃ] Voz 2: {nome_voz2}")
            
            # Pegar canal base
            canal_base = guild.get_channel(CANAL_BASE_CLANS_ID)
            if not canal_base:
                await interaction.followup.send("❌ Canal base não encontrado!", ephemeral=True)
                return
            
            # Pegar categoria base para copiar permissões
            categoria_base = guild.get_channel(CATEGORIA_BASE_ID)
            if categoria_base and hasattr(categoria_base, 'category') and categoria_base.category:
                categoria_modelo = categoria_base.category
            else:
                # Se o ID for de uma categoria diretamente
                categoria_modelo = discord.utils.get(guild.categories, id=CATEGORIA_BASE_ID)
            
            # Se não encontrou categoria modelo, usa a categoria do canal base
            if not categoria_modelo:
                categoria_modelo = canal_base.category
            
            if not categoria_modelo:
                await interaction.followup.send("❌ Não foi possível encontrar a categoria base!", ephemeral=True)
                return
            
            print(f"[CLÃ] Categoria modelo: {categoria_modelo.name}")
            
            # Criar categoria própria para o clã
            overwrites_categoria = {}
            
            # Copiar permissões da categoria modelo
            for target, overwrite in categoria_modelo.overwrites.items():
                overwrites_categoria[target] = overwrite
            
            # Adicionar permissão para o cargo do clã
            overwrites_categoria[cargo_cla] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                connect=True,
                speak=True,
                read_message_history=True
            )
            
            # Adicionar permissão para o bot
            overwrites_categoria[guild.me] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                connect=True
            )
            
            # Adicionar staff
            try:
                from modules.adm_system import load_adm_roles
                for role_name in load_adm_roles():
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role:
                        overwrites_categoria[role] = discord.PermissionOverwrite(
                            read_messages=True,
                            send_messages=True,
                            connect=True,
                            speak=True
                        )
            except:
                pass
            
            # Criar categoria
            nome_categoria = f"⚔️ {nome_cla}・"
            print(f"[CLÃ] Criando categoria: {nome_categoria}")
            
            categoria_cla = await guild.create_category(
                name=nome_categoria,
                overwrites=overwrites_categoria,
                reason=f"Categoria do clã {nome_cla}"
            )
            print(f"[CLÃ] ✅ Categoria criada: {categoria_cla.name}")
            
            # Overwrites para os canais (herdam da categoria, mas podemos adicionar específicos)
            overwrites_canais = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False, connect=False, speak=False),
                cargo_cla: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True, speak=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, connect=True)
            }
            
            # Criar canal de texto
            print(f"[CLÃ] Criando canal de texto: {nome_texto}")
            canal_texto = await guild.create_text_channel(
                name=nome_texto,
                category=categoria_cla,
                overwrites=overwrites_canais,
                topic=f"Clã: {nome_cla} | Dono: {user.name}"
            )
            print(f"[CLÃ] ✅ Texto: {canal_texto.name}")
            
            # Criar canal de voz 1
            print(f"[CLÃ] Criando canal de voz 1: {nome_voz1}")
            canal_voz1 = await guild.create_voice_channel(
                name=nome_voz1,
                category=categoria_cla,
                overwrites=overwrites_canais
            )
            print(f"[CLÃ] ✅ Voz 1: {canal_voz1.name}")
            
            # Criar canal de voz 2
            print(f"[CLÃ] Criando canal de voz 2: {nome_voz2}")
            canal_voz2 = await guild.create_voice_channel(
                name=nome_voz2,
                category=categoria_cla,
                overwrites=overwrites_canais
            )
            print(f"[CLÃ] ✅ Voz 2: {canal_voz2.name}")
            
            # Salvar
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
                print(f"[CLÃ] ✅ Dados salvos!")
            
            # Painel no canal de texto
            embed = discord.Embed(
                title="👥 ADICIONAR MEMBROS AO CLÃ",
                description=(
                    f"**Clã:** {nome_cla}\n"
                    f"**Dono:** {user.mention}\n\n"
                    "Para adicionar novos jogadores ao seu clã, clique no botão abaixo e cole o ID do jogador.\n\n"
                    f"✅ Limite gratuito: **{LIMITE_PADRAO} membros**.\n\n"
                    "💎 Para aumentar o limite, veja **#💎・𝐕𝐈𝐏𝐬**."
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Criado em: {datetime.now().strftime('%d/%m/%Y')}")
            
            view = PainelClaView(self, clan_id if clan_id else str(user.id), guild.id)
            await canal_texto.send(f"⚔️ **Bem-vindos ao clã {nome_cla}** ⚔️", embed=embed, view=view)
            
            # Responder ao usuário
            await interaction.followup.send(
                f"✅ **Clã criado!**\n\n"
                f"📁 Categoria: {categoria_cla.name}\n"
                f"📝 {canal_texto.mention}\n"
                f"🎙️ {canal_voz1.mention}\n"
                f"🎙️ {canal_voz2.mention}",
                ephemeral=True
            )
            
            print(f"[CLÃ] ========== CRIAÇÃO CONCLUÍDA ==========\n")
            
        except Exception as e:
            print(f"[CLÃ] ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(f"❌ Erro: {str(e)[:200]}", ephemeral=True)
            except:
                pass
    
    async def excluir_cla(self, interaction, clan_id):
        """Exclui completamente um clã (canais, categoria, cargo)"""
        try:
            guild = interaction.guild
            clans = carregar_clans(guild.id)
            clan_data = clans.get(clan_id)
            
            if not clan_data:
                await interaction.followup.send("❌ Clã não encontrado!", ephemeral=True)
                return
            
            print(f"\n[CLÃ] ========== EXCLUINDO CLÃ ==========")
            print(f"[CLÃ] Clã: {clan_data['nome']}")
            
            # Excluir canais
            canais = clan_data.get("canais", {})
            
            texto_id = canais.get("texto_id")
            if texto_id:
                canal = guild.get_channel(texto_id)
                if canal:
                    await canal.delete()
                    print(f"[CLÃ] ✅ Canal de texto excluído")
            
            voz1_id = canais.get("voz1_id")
            if voz1_id:
                canal = guild.get_channel(voz1_id)
                if canal:
                    await canal.delete()
                    print(f"[CLÃ] ✅ Canal de voz 1 excluído")
            
            voz2_id = canais.get("voz2_id")
            if voz2_id:
                canal = guild.get_channel(voz2_id)
                if canal:
                    await canal.delete()
                    print(f"[CLÃ] ✅ Canal de voz 2 excluído")
            
            # Excluir categoria
            categoria_id = clan_data.get("categoria_id")
            if categoria_id:
                categoria = guild.get_channel(categoria_id)
                if categoria:
                    await categoria.delete()
                    print(f"[CLÃ] ✅ Categoria excluída: {categoria.name}")
            
            # Excluir cargo
            cargo_id = clan_data.get("cargo_id")
            if cargo_id:
                cargo = guild.get_role(cargo_id)
                if cargo:
                    await cargo.delete()
                    print(f"[CLÃ] ✅ Cargo excluído: {cargo.name}")
            
            # Remover dos dados
            del clans[clan_id]
            salvar_clans(guild.id, clans)
            print(f"[CLÃ] ✅ Dados removidos da memória")
            
            await interaction.followup.send(
                f"✅ **Clã `{clan_data['nome']}` excluído com sucesso!**\n\n"
                f"🗑️ Canais excluídos\n"
                f"🗑️ Categoria excluída\n"
                f"🗑️ Cargo excluído",
                ephemeral=True
            )
            
            print(f"[CLÃ] ========== EXCLUSÃO CONCLUÍDA ==========\n")
            
        except Exception as e:
            print(f"[CLÃ] ❌ ERRO ao excluir: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(f"❌ Erro ao excluir: {str(e)[:200]}", ephemeral=True)
            except:
                pass
    
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
        
        view = PainelCriarClaView(self.bot)
        
        await ctx.send(embed=embed, view=view)
        await ctx.message.delete()
        
        print(f"✅ Painel de clãs configurado em #{ctx.channel.name}")

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(ClansCog(bot))
    print("✅ Sistema de Clãs configurado!")
