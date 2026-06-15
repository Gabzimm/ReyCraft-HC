import discord
from discord.ext import commands
import asyncio
from datetime import datetime

# ========== CONFIGURAÇÃO ==========
# ID do canal que será monitorado (QUALQUER MENSAGEM = BAN)
CANAL_ISCA_ID = 1515455518423126310  # ← COLOQUE O ID DO CANAL AQUI!

# ID do canal de log (para staff ver quem foi banido)
CANAL_LOG_ID = 1516086738525753374  # ← COLOQUE O ID DO CANAL DE LOG AQUI!

# ========== FUNÇÃO PARA VERIFICAR SE É STAFF (NÃO BANIR STAFF) ==========
def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro é staff (para não banir staff acidentalmente)"""
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # Admin do Discord
    if member.guild_permissions.administrator:
        return True
    
    # Verificar cargos staff
    try:
        from modules.adm_system import is_staff as adm_is_staff
        return adm_is_staff(member)
    except:
        return member.guild_permissions.manage_guild

# ========== COG PRINCIPAL ==========
class AntiGolpeCog(commands.Cog):
    """Sistema Anti-Golpe - Bane automaticamente quem enviar mensagem no canal isca"""
    
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Anti-Golpe carregado!")
    
    async def banir_usuario(self, member: discord.Member, motivo: str, mensagem: str, canal):
        """Função para banir usuário e apagar mensagens"""
        try:
            # Apagar todas as mensagens do usuário nos últimos 7 dias
            await member.ban(reason=motivo, delete_message_days=7)
            
            # Enviar log
            await self.enviar_log(member, motivo, mensagem, canal)
            
            print(f"✅ Usuário {member.name} banido! Motivo: {motivo}")
            return True
            
        except discord.Forbidden:
            print(f"❌ Sem permissão para banir {member.name}")
            return False
        except Exception as e:
            print(f"❌ Erro ao banir {member.name}: {e}")
            return False
    
    async def enviar_log(self, member: discord.Member, motivo: str, mensagem: str, canal):
        """Envia log do banimento para o canal de staff"""
        canal_log = self.bot.get_channel(CANAL_LOG_ID)
        
        if not canal_log:
            print(f"⚠️ Canal de log não encontrado! ID: {CANAL_LOG_ID}")
            return
        
        embed = discord.Embed(
            title="🔨 USUÁRIO BANIDO - CANAL ISCA",
            description=f"**Usuário:** {member.mention}\n"
                       f"**ID:** `{member.id}`\n"
                       f"**Nome:** {member.name}\n\n"
                       f"**Motivo:** {motivo}\n"
                       f"**Mensagem enviada:** ```{mensagem[:500]}```\n"
                       f"**Canal:** {canal.mention}\n\n"
                       f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            color=discord.Color.red()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Total de membros após ban: {member.guild.member_count - 1}")
        
        await canal_log.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Monitora mensagens no canal isca - QUALQUER MENSAGEM = BAN"""
        
        # Ignorar mensagens do próprio bot
        if message.author.bot:
            return
        
        # Verificar se é no canal isca
        if message.channel.id != CANAL_ISCA_ID:
            return
        
        # Verificar se o autor é staff (não banir staff)
        if is_staff(message.author):
            # Se for staff, apenas apagar a mensagem e avisar
            await message.delete()
            aviso = await message.channel.send(
                f"⚠️ {message.author.mention}, você é staff e está no canal de isca! "
                f"Sua mensagem foi apagada para não ativar o sistema."
            )
            await asyncio.sleep(5)
            await aviso.delete()
            return
        
        # BANIR O USUÁRIO IMEDIATAMENTE
        motivo = f"Enviou mensagem no canal de isca ({message.channel.name})"
        
        # Banir e apagar todas as mensagens
        await self.banir_usuario(message.author, motivo, message.content, message.channel)
        
        # Tentar apagar a mensagem que ativou o ban (já será apagada pelo ban)

    @commands.command(name="setup_antigolpe")
    @commands.has_permissions(administrator=True)
    async def setup_antigolpe(self, ctx):
        """
        🔒 Configura o canal de isca anti-golpe
        
        Cria um canal onde QUALQUER mensagem resulta em banimento imediato
        """
        
        # Criar embed de aviso
        embed = discord.Embed(
            title="⚠️ NÃO ENVIE MENSAGENS AQUI",
            description=(
                "Você receberá um **banimento imediato** se enviar mensagens neste canal\n\n"
                "Isso serve para remover usuários **self-bot** que mandam spam em todos os canais "
                "do servidor tentando infectar mais usuários"
            ),
            color=discord.Color.red()
        )
        
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1086845746548527184.png")
        
        # Enviar mensagem fixa no canal
        await ctx.send(embed=embed)
        
        # Fixar a mensagem no canal
        msg = await ctx.send("📌 **Mensagem fixada - NÃO ENVIAR MENSAGENS AQUI!**")
        await msg.pin()
        
        print(f"✅ Canal anti-golpe configurado em #{ctx.channel.name}")
    
    @commands.command(name="set_canal_isca")
    @commands.has_permissions(administrator=True)
    async def set_canal_isca(self, ctx, canal: discord.TextChannel = None):
        """
        🔧 Define o canal atual como canal isca
        
        Use: !set_canal_isca #canal
        """
        global CANAL_ISCA_ID
        
        if canal is None:
            canal = ctx.channel
        
        CANAL_ISCA_ID = canal.id
        
        # Salvar em arquivo para persistência
        import json
        import os
        
        config_data = {
            "canal_isca_id": CANAL_ISCA_ID,
            "canal_log_id": CANAL_LOG_ID
        }
        
        with open("antigolpe_config.json", "w") as f:
            json.dump(config_data, f, indent=4)
        
        # Enviar embed de aviso no canal
        embed = discord.Embed(
            title="⚠️ NÃO ENVIE MENSAGENS AQUI",
            description=(
                "Você receberá um **banimento imediato** se enviar mensagens neste canal\n\n"
                "Isso serve para remover usuários **self-bot** que mandam spam em todos os canais "
                "do servidor tentando infectar mais usuários"
            ),
            color=discord.Color.red()
        )
        
        await canal.send(embed=embed)
        
        # Fixar a mensagem
        msg = await canal.send("📌 **CANAL ISCA ATIVADO - NÃO ENVIAR MENSAGENS!**")
        await msg.pin()
        
        await ctx.send(f"✅ Canal {canal.mention} configurado como CANAL ISCA com sucesso!")

    @commands.command(name="set_canal_log_antigolpe")
    @commands.has_permissions(administrator=True)
    async def set_canal_log(self, ctx, canal: discord.TextChannel):
        """
        🔧 Define o canal de log dos bans
        
        Use: !set_canal_log_antigolpe #canal
        """
        global CANAL_LOG_ID
        
        CANAL_LOG_ID = canal.id
        
        # Salvar config
        import json
        import os
        
        config_data = {}
        if os.path.exists("antigolpe_config.json"):
            with open("antigolpe_config.json", "r") as f:
                config_data = json.load(f)
        
        config_data["canal_log_id"] = CANAL_LOG_ID
        config_data["canal_isca_id"] = CANAL_ISCA_ID
        
        with open("antigolpe_config.json", "w") as f:
            json.dump(config_data, f, indent=4)
        
        await ctx.send(f"✅ Canal {canal.mention} configurado como canal de LOG do anti-golpe!")

# ========== CARREGAR CONFIGURAÇÃO SALVA ==========
def carregar_config():
    """Carrega as configurações salvas do arquivo"""
    global CANAL_ISCA_ID, CANAL_LOG_ID
    
    import json
    import os
    
    if os.path.exists("antigolpe_config.json"):
        try:
            with open("antigolpe_config.json", "r") as f:
                config = json.load(f)
                CANAL_ISCA_ID = config.get("canal_isca_id", CANAL_ISCA_ID)
                CANAL_LOG_ID = config.get("canal_log_id", CANAL_LOG_ID)
                print(f"✅ Configuração anti-golpe carregada: Canal isca ID: {CANAL_ISCA_ID}")
        except:
            pass

# Carregar configuração
carregar_config()

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(AntiGolpeCog(bot))
    print("✅ Sistema Anti-Golpe configurado!")
