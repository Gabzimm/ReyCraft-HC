import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import json
import os
import asyncio

# ========== ARQUIVO DE CONFIGURAÇÃO ==========
DATA_FILE = "adm_roles.json"

def load_adm_roles():
    """Carrega a lista de cargos ADM do arquivo"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_adm_roles(roles):
    """Salva a lista de cargos ADM no arquivo"""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(roles, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar ADM roles: {e}")

# ========== FUNÇÃO PARA VERIFICAR SE É OWNER (DONO OU CARGO OWNER) ==========
def is_owner(member: discord.Member) -> bool:
    """
    Verifica se o membro é DONO do servidor ou tem cargo com nome "Owner"
    """
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # Verificar se tem algum cargo com "Owner" no nome (case insensitive)
    for role in member.roles:
        if "owner" in role.name.lower():
            return True
    
    return False

# ========== FUNÇÃO PARA VERIFICAR PERMISSÃO DE STAFF ==========
def is_staff(member: discord.Member) -> bool:
    """
    Verifica se o membro tem permissão de staff:
    - Dono do servidor ✅
    - Cargo com "Owner" no nome ✅
    - Admin do Discord ✅
    - Cargo ADM configurado via !adm ✅
    """
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # Cargo Owner
    for role in member.roles:
        if "owner" in role.name.lower():
            return True
    
    # Admin do Discord
    if member.guild_permissions.administrator:
        return True
    
    # Carregar cargos ADM configurados
    adm_role_names = load_adm_roles()
    
    # Verificar se tem algum cargo ADM configurado
    for role in member.roles:
        if role.name in adm_role_names:
            return True
    
    return False

# ========== FUNÇÃO PARA VERIFICAR SE PODE USAR !ADM (APENAS OWNER/ADMIN) ==========
def can_use_adm_command(member: discord.Member) -> bool:
    """
    Quem pode usar !adm:
    - Dono do servidor
    - Cargos com "Owner" no nome
    """
    if not member:
        return False
    
    if member.id == member.guild.owner_id:
        return True
    
    for role in member.roles:
        if "owner" in role.name.lower():
            return True
    
    return False

# ========== MODAL PARA ESCOLHER CARGO ==========
class EscolherCargoModal(ui.Modal, title="➕ Adicionar Cargo ADM"):
    nome_cargo = ui.TextInput(
        label="Nome exato do cargo:",
        placeholder="Ex: 👑 ADM, Moderador, Admin, etc.",
        required=True,
        max_length=100
    )
    
    def __init__(self, cog, ctx, modo="add"):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
        self.modo = modo
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        nome = self.nome_cargo.value.strip()
        cargo = discord.utils.get(interaction.guild.roles, name=nome)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo `{nome}` não encontrado!", ephemeral=True)
            return
        
        adm_roles = load_adm_roles()
        
        if self.modo == "add":
            if cargo.name in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` já é um ADM!", ephemeral=True)
                return
            
            adm_roles.append(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM!", ephemeral=True)
        
        elif self.modo == "remove":
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista!", ephemeral=True)
                return
            
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista!", ephemeral=True)

# ========== VIEW DE LISTA DE CARGOS ==========
class ListaCargosView(ui.View):
    def __init__(self, cog, ctx, modo, current_page=0):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.modo = modo
        self.current_page = current_page
        
        all_roles = [role for role in ctx.guild.roles if role.name != "@everyone"]
        self.total_roles = len(all_roles)
        
        self.roles_per_page = 24
        self.total_pages = max(1, (self.total_roles + self.roles_per_page - 1) // self.roles_per_page)
        
        start_idx = current_page * self.roles_per_page
        end_idx = min(start_idx + self.roles_per_page, self.total_roles)
        self.current_roles = all_roles[start_idx:end_idx]
        
        self.dropdown = ui.Select(
            placeholder=f"🔽 Selecione um cargo (Página {current_page + 1}/{self.total_pages})",
            min_values=1,
            max_values=1,
            row=0
        )
        
        for role in self.current_roles:
            emoji = role.unicode_emoji if role.unicode_emoji else "📌"
            self.dropdown.add_option(
                label=role.name[:100],
                value=role.name,
                emoji=emoji
            )
        
        self.dropdown.callback = self.dropdown_callback
        self.add_item(self.dropdown)
        
        if self.total_pages > 1:
            if current_page > 0:
                prev_btn = ui.Button(label="◀️ Anterior", style=ButtonStyle.secondary, row=1)
                prev_btn.callback = self.previous_page
                self.add_item(prev_btn)
            
            if current_page < self.total_pages - 1:
                next_btn = ui.Button(label="Próxima ▶️", style=ButtonStyle.secondary, row=1)
                next_btn.callback = self.next_page
                self.add_item(next_btn)
    
    async def dropdown_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        nome_cargo = self.dropdown.values[0]
        cargo = discord.utils.get(interaction.guild.roles, name=nome_cargo)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo não encontrado!", ephemeral=True)
            return
        
        adm_roles = load_adm_roles()
        
        if self.modo == "add":
            if cargo.name in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` já é um ADM!", ephemeral=True)
                return
            
            adm_roles.append(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM!", ephemeral=True)
        
        elif self.modo == "remove":
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista!", ephemeral=True)
                return
            
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista!", ephemeral=True)
        
        self.clear_items()
        await interaction.message.edit(view=self)
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        new_view = ListaCargosView(self.cog, self.ctx, self.modo, self.current_page - 1)
        await interaction.response.edit_message(view=new_view)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        new_view = ListaCargosView(self.cog, self.ctx, self.modo, self.current_page + 1)
        await interaction.response.edit_message(view=new_view)

# ========== VIEW PRINCIPAL DO PAINEL ADM ==========
class AdmPainelView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="➕ Adicionar ADM", style=ButtonStyle.success, emoji="➕", row=0)
    async def add_adm(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="➕ Adicionar Cargo ADM",
            description=(
                "**Como adicionar:**\n"
                "1️⃣ Clique em **Digitar Nome** para digitar o nome exato\n"
                "2️⃣ Clique em **Selecionar da Lista** para escolher um cargo\n\n"
                "⚠️ **Apenas cargos já existentes no servidor**"
            ),
            color=discord.Color.green()
        )
        
        view = ui.View(timeout=120)
        
        digitar_btn = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary)
        
        async def digitar_callback(interaction):
            modal = EscolherCargoModal(self.cog, self.ctx, modo="add")
            await interaction.response.send_modal(modal)
        
        digitar_btn.callback = digitar_callback
        
        selecionar_btn = ui.Button(label="📋 Selecionar da Lista", style=ButtonStyle.secondary)
        
        async def selecionar_callback(interaction):
            view_lista = ListaCargosView(self.cog, self.ctx, modo="add")
            await interaction.response.edit_message(embed=embed, view=view_lista)
        
        selecionar_btn.callback = selecionar_callback
        
        view.add_item(digitar_btn)
        view.add_item(selecionar_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="➖ Remover ADM", style=ButtonStyle.danger, emoji="➖", row=0)
    async def remove_adm(self, interaction: discord.Interaction, button: ui.Button):
        adm_roles = load_adm_roles()
        
        if not adm_roles:
            embed = discord.Embed(
                title="❌ Nenhum ADM Configurado",
                description="Não há cargos ADM configurados para remover!",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="➖ Remover Cargo ADM",
            description=(
                "**Como remover:**\n"
                "1️⃣ Clique em **Digitar Nome**\n"
                "2️⃣ Clique em **Selecionar da Lista**\n\n"
                f"**📋 ADMs atuais:** {', '.join(adm_roles)}"
            ),
            color=discord.Color.orange()
        )
        
        view = ui.View(timeout=120)
        
        digitar_btn = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary)
        
        async def digitar_callback(interaction):
            modal = EscolherCargoModal(self.cog, self.ctx, modo="remove")
            await interaction.response.send_modal(modal)
        
        digitar_btn.callback = digitar_callback
        
        selecionar_btn = ui.Button(label="📋 Selecionar da Lista", style=ButtonStyle.secondary)
        
        async def selecionar_callback(interaction):
            view_lista = ListaCargosView(self.cog, self.ctx, modo="remove")
            await interaction.response.edit_message(embed=embed, view=view_lista)
        
        selecionar_btn.callback = selecionar_callback
        
        view.add_item(digitar_btn)
        view.add_item(selecionar_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @ui.button(label="📋 Lista de ADMs", style=ButtonStyle.secondary, emoji="📋", row=1)
    async def list_adms(self, interaction: discord.Interaction, button: ui.Button):
        adm_roles = load_adm_roles()
        
        if not adm_roles:
            embed = discord.Embed(
                title="📋 Lista de ADMs",
                description="❌ Nenhum cargo ADM configurado ainda!",
                color=discord.Color.red()
            )
        else:
            lista = "\n".join([f"🔹 `{role}`" for role in adm_roles])
            embed = discord.Embed(
                title="📋 **Cargos com Permissão de Staff**",
                description=f"**Total:** {len(adm_roles)}\n\n{lista}\n\n✅ Esses cargos podem usar comandos de staff!",
                color=discord.Color.blue()
            )
        
        await interaction.response.edit_message(embed=embed, view=self)

# ========== COG PRINCIPAL ==========
class AdmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo ADM System carregado!")
    
    async def atualizar_painel(self, interaction: discord.Interaction):
        adm_roles = load_adm_roles()
        
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=(
                "Aqui você pode gerenciar quais cargos terão **permissão de staff**.\n\n"
                f"**📋 Staffs atuais:**\n"
                f"{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_footer(text="⚠️ Apenas Dono ou Owners podem alterar essas configurações")
        
        view = AdmPainelView(self, await self.bot.get_context(interaction.message))
        await interaction.edit_original_response(embed=embed, view=view)
    
    @commands.command(name="adm")
    async def adm_painel(self, ctx):
        """
        👑 Painel de gerenciamento de ADMs
        
        **Apenas Dono do servidor ou cargos "Owner" podem usar!**
        """
        
        # Usar a nova função can_use_adm_command
        from modules.adm_system import can_use_adm_command
        
        if not can_use_adm_command(ctx.author):
            msg = await ctx.send("❌ **Apenas o Dono do servidor ou cargos com 'Owner' podem usar este comando!**")
            await asyncio.sleep(3)
            await msg.delete()
            await ctx.message.delete()
            return
        
        try:
            await ctx.message.delete()
        except:
            pass
        
        adm_roles = load_adm_roles()
        
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=(
                "Aqui você pode gerenciar quais cargos terão **permissão de staff**.\n\n"
                f"**📋 Staffs atuais:**\n"
                f"{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_footer(text="⚠️ Apenas Dono ou Owners podem alterar essas configurações")
        
        view = AdmPainelView(self, ctx)
        await ctx.send(embed=embed, view=view)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(AdmCog(bot))
    print("✅ Sistema de ADM configurado!")
