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

# ========== FUNÇÃO AUXILIAR PARA VERIFICAR PERMISSÃO ==========
def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro tem permissão de staff (ADM configurado ou admin/dono)"""
    if not member:
        return False
    
    # Dono do servidor sempre pode
    if member.id == member.guild.owner_id:
        return True
    
    # Admin do Discord sempre pode
    if member.guild_permissions.administrator:
        return True
    
    # Carregar cargos ADM configurados
    adm_role_names = load_adm_roles()
    
    # Verificar se tem algum cargo ADM configurado
    for role in member.roles:
        if role.name in adm_role_names:
            return True
    
    return False

# ========== FUNÇÃO PARA APAGAR MENSAGEM DEPOIS DE TEMPO ==========
async def delete_after(ctx, message, delay=3):
    """Apaga uma mensagem após X segundos"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except:
        pass

# ========== MODAL PARA ESCOLHER CARGO ==========
class EscolherCargoModal(ui.Modal, title="➕ Adicionar Cargo ADM"):
    """Modal para digitar o nome do cargo"""
    
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
        self.modo = modo  # "add" ou "remove"
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        nome = self.nome_cargo.value.strip()
        
        # Verificar se o cargo existe no servidor
        cargo = discord.utils.get(interaction.guild.roles, name=nome)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo `{nome}` não encontrado no servidor!", ephemeral=True)
            return
        
        adm_roles = load_adm_roles()
        
        if self.modo == "add":
            if cargo.name in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` já é um ADM!", ephemeral=True)
                return
            
            adm_roles.append(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM com sucesso!", ephemeral=True)
        
        elif self.modo == "remove":
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista de ADMs!", ephemeral=True)
                return
            
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista de ADMs!", ephemeral=True)

# ========== VIEW DE LISTA DE CARGOS (DROPDOWN) ==========
class ListaCargosView(ui.View):
    """View com dropdown para escolher cargo do servidor"""
    
    def __init__(self, cog, ctx, modo):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.modo = modo  # "add" ou "remove"
        
        # Criar dropdown com todos os cargos do servidor
        self.dropdown = ui.Select(
            placeholder="🔽 Selecione um cargo...",
            min_values=1,
            max_values=1,
            row=0
        )
        
        # Adicionar opções (limitar a 25)
        for role in ctx.guild.roles[:25]:
            if role.name != "@everyone":
                emoji = role.unicode_emoji if role.unicode_emoji else "📌"
                self.dropdown.add_option(
                    label=role.name[:100],
                    value=role.name,
                    emoji=emoji,
                    description=f"ID: {role.id}"
                )
        
        self.dropdown.callback = self.dropdown_callback
        self.add_item(self.dropdown)
    
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
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` adicionado como ADM com sucesso!", ephemeral=True)
        
        elif self.modo == "remove":
            if cargo.name not in adm_roles:
                await interaction.followup.send(f"❌ Cargo `{cargo.name}` não está na lista de ADMs!", ephemeral=True)
                return
            
            adm_roles.remove(cargo.name)
            save_adm_roles(adm_roles)
            await interaction.followup.send(f"✅ Cargo `{cargo.name}` removido da lista de ADMs!", ephemeral=True)
        
        # Limpar a view depois de usar
        self.clear_items()
        await interaction.message.edit(view=self)

# ========== VIEW PRINCIPAL DO PAINEL ADM ==========
class AdmPainelView(ui.View):
    """Painel principal do sistema ADM"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verifica se quem clicou é o dono"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas o dono pode usar este painel!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="➕ Adicionar ADM", style=ButtonStyle.success, emoji="➕", row=0)
    async def add_adm(self, interaction: discord.Interaction, button: ui.Button):
        embed = discord.Embed(
            title="➕ Adicionar Cargo ADM",
            description=(
                "**Como adicionar:**\n"
                "1️⃣ Clique em **Digitar Nome** para digitar o nome exato do cargo\n"
                "2️⃣ Clique em **Selecionar da Lista** para escolher um cargo da lista\n\n"
                "⚠️ **Apenas cargos já existentes no servidor**"
            ),
            color=discord.Color.green()
        )
        
        view = ui.View(timeout=60)
        
        # Botão para digitar nome
        digitar_btn = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary)
        
        async def digitar_callback(interaction):
            modal = EscolherCargoModal(self.cog, self.ctx, modo="add")
            await interaction.response.send_modal(modal)
        
        digitar_btn.callback = digitar_callback
        
        # Botão para selecionar da lista
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
                "1️⃣ Clique em **Digitar Nome** para digitar o nome exato do cargo\n"
                "2️⃣ Clique em **Selecionar da Lista** para escolher um cargo da lista\n\n"
                f"**📋 ADMs atuais:** {', '.join(adm_roles) if adm_roles else 'Nenhum'}"
            ),
            color=discord.Color.orange()
        )
        
        view = ui.View(timeout=60)
        
        # Botão para digitar nome
        digitar_btn = ui.Button(label="✏️ Digitar Nome", style=ButtonStyle.primary)
        
        async def digitar_callback(interaction):
            modal = EscolherCargoModal(self.cog, self.ctx, modo="remove")
            await interaction.response.send_modal(modal)
        
        digitar_btn.callback = digitar_callback
        
        # Botão para selecionar da lista
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
            lista_formatada = "\n".join([f"🔹 `{role}`" for role in adm_roles])
            
            embed = discord.Embed(
                title="📋 **Cargos com Permissão de Staff**",
                description=(
                    f"**Total:** {len(adm_roles)}\n\n"
                    f"{lista_formatada}\n\n"
                    "✅ Esses cargos podem usar comandos de staff!"
                ),
                color=discord.Color.blue()
            )
        
        await interaction.response.edit_message(embed=embed, view=self)

# ========== COG PRINCIPAL ==========
class AdmCog(commands.Cog):
    """Sistema de Gerenciamento de ADMs"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo ADM System carregado!")
    
    @commands.command(name="adm")
    async def adm_painel(self, ctx):
        """
        👑 Painel de gerenciamento de ADMs
        
        **Apenas o Dono do servidor pode usar!**
        
        Use este comando para:
        - Adicionar cargos como ADM
        - Remover cargos ADM
        - Ver lista de ADMs configurados
        """
        
        # Verificar se é o dono
        if ctx.author.id != ctx.guild.owner_id:
            msg = await ctx.send("❌ **Apenas o Dono do servidor pode usar este comando!**")
            await asyncio.sleep(3)
            await msg.delete()
            await ctx.message.delete()
            return
        
        # Apagar o comando do usuário
        try:
            await ctx.message.delete()
        except:
            pass
        
        adm_roles = load_adm_roles()
        
        embed = discord.Embed(
            title="👑 **Sistema de Gerenciamento de Staff**",
            description=(
                "Aqui você pode gerenciar quais cargos terão **permissão de staff** no bot.\n\n"
                "**📌 O que são Staff?**\n"
                "Cargos configurados aqui poderão usar:\n"
                "🔹 Comandos de limpeza (`!limpar`)\n"
                "🔹 Sistema de tickets (`!setup_tickets`)\n"
                "🔹 Acesso a tickets como staff\n\n"
                f"**📋 Staffs atuais:**\n"
                f"{', '.join(adm_roles) if adm_roles else 'Nenhum cargo configurado'}"
            ),
            color=discord.Color.purple()
        )
        
        embed.set_footer(text="⚠️ Apenas você (Dono) pode alterar essas configurações")
        
        view = AdmPainelView(self, ctx)
        await ctx.send(embed=embed, view=view)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(AdmCog(bot))
    print("✅ Sistema de ADM configurado!")
