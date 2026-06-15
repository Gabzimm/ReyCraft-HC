import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import asyncio
from datetime import datetime
from utils.memory import load_guild_data, is_staff

# Importar sistema ADM
try:
    from modules.adm_system import is_staff
except ImportError:
    from adm_system import is_staff

# ========== FUNÇÕES AUXILIARES ==========
def usuario_pode_limpar(member: discord.Member) -> bool:
    """Verifica se o usuário pode usar comandos de limpeza"""
    return is_staff(member)

# ========== VIEW DE CONFIRMAÇÃO ==========
class ConfirmarLimpezaView(ui.View):
    """View para confirmar limpeza"""
    
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
        
        # Deletar mensagens
        await self.cog.realizar_limpeza(self.ctx, self.quantidade, self.canal)
        
        # Apagar mensagem de confirmação
        await interaction.message.delete()
    
    @ui.button(label="❌ Cancelar", style=ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await interaction.message.delete()
        msg = await self.ctx.send("❌ Limpeza cancelada.")
        await asyncio.sleep(3)
        await msg.delete()

# ========== MODAL DE LIMPEZA ==========
class LimpezaQuantidadeModal(ui.Modal, title="🧹 Limpar por Quantidade"):
    """Modal para limpar por quantidade"""
    
    quantidade = ui.TextInput(
        label="Quantidade de mensagens:",
        placeholder="Ex: 50 (máximo 999)",
        required=True,
        max_length=3
    )
    
    canal_id = ui.TextInput(
        label="ID do canal (opcional):",
        placeholder="Deixe vazio para o canal atual",
        required=False,
        max_length=20
    )
    
    def __init__(self, cog, ctx):
        super().__init__()
        self.cog = cog
        self.ctx = ctx
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Validar quantidade
        if not self.quantidade.value.isdigit():
            await interaction.followup.send("❌ Quantidade deve ser um número!", ephemeral=True)
            return
        
        qtd = int(self.quantidade.value)
        if qtd < 1 or qtd > 999:
            await interaction.followup.send("❌ Quantidade deve ser entre 1 e 999!", ephemeral=True)
            return
        
        # Validar canal
        canal = self.ctx.channel
        if self.canal_id.value and self.canal_id.value.strip():
            if not self.canal_id.value.isdigit():
                await interaction.followup.send("❌ ID do canal inválido!", ephemeral=True)
                return
            
            canal = self.ctx.guild.get_channel(int(self.canal_id.value))
            if not canal:
                await interaction.followup.send("❌ Canal não encontrado!", ephemeral=True)
                return
        
        # Mostrar confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Limpeza",
            description=(
                f"**Canal:** {canal.mention}\n"
                f"**Quantidade:** {qtd} mensagens\n\n"
                "Tem certeza que deseja continuar?"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmarLimpezaView(self.cog, self.ctx, qtd, canal)
        await interaction.followup.send(embed=embed, view=view)

# ========== VIEW PRINCIPAL ==========
class LimpezaView(ui.View):
    """View principal com botões"""
    
    def __init__(self, cog, ctx):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Apenas quem executou pode usar!", ephemeral=True)
            return False
        return True
    
    @ui.button(label="🧹 Limpar por Quantidade", style=ButtonStyle.primary, emoji="🔢", row=0)
    async def limpar_quantidade(self, interaction: discord.Interaction, button: ui.Button):
        modal = LimpezaQuantidadeModal(self.cog, self.ctx)
        await interaction.response.send_modal(modal)

# ========== COG PRINCIPAL ==========
class LimpezaCog(commands.Cog):
    """Sistema de Limpeza de Canais"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Limpeza carregado!")
    
    async def realizar_limpeza(self, ctx, quantidade: int, canal: discord.TextChannel):
        """Realiza a limpeza de mensagens"""
        try:
            # Deletar mensagens (incluindo o comando)
            deleted = await canal.purge(limit=quantidade + 1)
            
            # Mensagem de confirmação
            embed = discord.Embed(
                title="🧹 Limpeza Concluída",
                description=(
                    f"**Canal:** {canal.mention}\n"
                    f"**Mensagens apagadas:** {len(deleted) - 1}\n"
                    f"**Responsável:** {ctx.author.mention}\n"
                    f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                ),
                color=discord.Color.green()
            )
            
            msg = await ctx.send(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
            
        except discord.Forbidden:
            msg = await ctx.send("❌ Não tenho permissão para apagar mensagens neste canal!")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception as e:
            msg = await ctx.send(f"❌ Erro: {e}")
            await asyncio.sleep(5)
            await msg.delete()
    
    @commands.command(name="limpar", aliases=["clean", "clear"])
    async def limpar(self, ctx, quantidade: int = None, canal: discord.TextChannel = None):
        """
        🧹 Comando de limpeza
        
        Uso:
        !limpar           - Mostra menu interativo
        !limpar 10        - Apaga 10 mensagens
        !limpar 50 #canal - Apaga 50 mensagens em outro canal
        !limpar 100       - Apaga 100 mensagens
        """
        
        # Verificar permissão
        if not usuario_pode_limpar(ctx.author):
            msg = await ctx.send("❌ Você não tem permissão para usar este comando!")
            await asyncio.sleep(5)
            await msg.delete()
            try:
                await ctx.message.delete()
            except:
                pass
            return
        
        # Apagar comando do usuário
        try:
            await ctx.message.delete()
        except:
            pass
        
        # Se não especificou quantidade, mostra menu interativo
        if quantidade is None:
            embed = discord.Embed(
                title="🧹 Sistema de Limpeza",
                description="Clique no botão abaixo para limpar mensagens:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📌 Uso Rápido",
                value=(
                    "`!limpar 10` - Apaga 10 mensagens\n"
                    "`!limpar 50` - Apaga 50 mensagens\n"
                    "`!limpar 100 #canal` - Apaga em outro canal"
                ),
                inline=False
            )
            
            embed.set_footer(text="Use !limpar [quantidade] para limpeza direta")
            
            view = LimpezaView(self, ctx)
            await ctx.send(embed=embed, view=view)
            return
        
        # Verificar quantidade
        if quantidade < 1 or quantidade > 999:
            msg = await ctx.send("❌ Quantidade deve ser entre 1 e 999!")
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        # Definir canal alvo
        canal_alvo = canal or ctx.channel
        
        # LIMPEZA DIRETA - SEM CONFIRMAÇÃO
        await self.realizar_limpeza(ctx, quantidade, canal_alvo)
    
    @commands.command(name="limpar_confirmar")
    async def limpar_com_confirmacao(self, ctx, quantidade: int, canal: discord.TextChannel = None):
        """🧹 Limpa mensagens com confirmação"""
        
        if not usuario_pode_limpar(ctx.author):
            msg = await ctx.send("❌ Você não tem permissão!")
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        if quantidade < 1 or quantidade > 999:
            msg = await ctx.send("❌ Quantidade deve ser entre 1 e 999!")
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        canal_alvo = canal or ctx.channel
        
        # Mostrar confirmação
        embed = discord.Embed(
            title="⚠️ Confirmar Limpeza",
            description=(
                f"**Canal:** {canal_alvo.mention}\n"
                f"**Quantidade:** {quantidade} mensagens\n\n"
                "Tem certeza que deseja continuar?"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmarLimpezaView(self, ctx, quantidade, canal_alvo)
        await ctx.send(embed=embed, view=view)

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(LimpezaCog(bot))
    print("✅ Sistema de Limpeza configurado!")
