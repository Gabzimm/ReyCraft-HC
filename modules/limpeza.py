import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime

# ========== FUNÇÃO STAFF (SIMPLIFICADA) ==========
def is_staff(member: discord.Member) -> bool:
    if not member:
        return False
    if member.id == member.guild.owner_id:
        return True
    for role in member.roles:
        if "owner" in role.name.lower():
            return True
    if member.guild_permissions.administrator:
        return True
    return False

# ========== VIEW DE CONFIRMAÇÃO ==========
class ConfirmarLimpezaView(ui.View):
    def __init__(self, cog, ctx, quantidade: int, canal: discord.TextChannel = None):
        super().__init__(timeout=30)
        self.cog = cog
        self.ctx = ctx
        self.quantidade = quantidade
        self.canal = canal or ctx.channel
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode confirmar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="✅ Confirmar", style=ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.cog.realizar_limpeza(self.ctx, self.quantidade, self.canal)
        await interaction.message.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()
        msg = await self.ctx.send("❌ Limpeza cancelada.")
        await asyncio.sleep(3)
        await msg.delete()

# ========== MODAL ==========
class LimpezaQuantidadeModal(ui.Modal, title="🧹 Limpar por Quantidade"):
    quantidade = ui.TextInput(label="Quantidade:", placeholder="Ex: 50 (máximo 999)", required=True, max_length=3)
    canal_id = ui.TextInput(label="ID do canal:", placeholder="Deixe vazio para o canal atual", required=False, max_length=20)
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        if not self.quantidade.value.isdigit():
            await interaction.followup.send("❌ Quantidade deve ser um número!", ephemeral=True)
            return
        
        qtd = int(self.quantidade.value)
        if qtd < 1 or qtd > 999:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 999!", ephemeral=True)
            return
        
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        embed = discord.Embed(title="⚠️ Confirmar Limpeza", description=f"**Canal:** {canal.mention}\n**Quantidade:** {qtd} mensagens\n\nTem certeza?", color=discord.Color.orange())
        view = ConfirmarLimpezaView(self.cog, self.ctx, qtd, canal)
        await interaction.followup.send(embed=embed, view=view)

# ========== VIEW PRINCIPAL ==========
class LimpezaView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="🧹 Limpar por Quantidade", style=ButtonStyle.primary, emoji="🔢")
    async def limpar_quantidade(self, interaction: discord.Interaction, button: ui.Button):
        modal = LimpezaQuantidadeModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)

# ========== COG ==========
class LimpezaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Limpeza carregado!")
    
    async def realizar_limpeza(self, ctx, quantidade: int, canal: discord.TextChannel):
        try:
            deleted = await canal.purge(limit=quantidade + 1)
            embed = discord.Embed(title="🧹 Limpeza Concluída", description=f"**Canal:** {canal.mention}\n**Mensagens apagadas:** {len(deleted) - 1}\n**Responsável:** {ctx.author.mention}", color=discord.Color.green())
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            msg = await ctx.send(f"❌ Erro: {e}")
            await asyncio.sleep(5)
            await msg.delete()
    
    @commands.command(name="limpar", aliases=["clean", "clear"])
    async def limpar(self, ctx, quantidade: int = None, canal: discord.TextChannel = None):
        if not is_staff(ctx.author):
            msg = await ctx.send("❌ Você não tem permissão para usar este comando!")
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        try:
            await ctx.message.delete()
        except:
            pass
        
        if quantidade is None:
            embed = discord.Embed(title="🧹 Sistema de Limpeza", description="Clique no botão abaixo para limpar mensagens:", color=discord.Color.blue())
            embed.add_field(name="📌 Uso Rápido", value="`!limpar 10` - Apaga 10 mensagens\n`!limpar 50` - Apaga 50 mensagens", inline=False)
            view = LimpezaView(self, ctx)
            await ctx.send(embed=embed, view=view)
            return
        
        if quantidade < 1 or quantidade > 999:
            msg = await ctx.send("❌ Quantidade deve ser entre 1 e 999!")
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        canal_alvo = canal or ctx.channel
        await self.realizar_limpeza(ctx, quantidade, canal_alvo)

async def setup(bot):
    await bot.add_cog(LimpezaCog(bot))
    print("✅ Sistema de Limpeza configurado!")
