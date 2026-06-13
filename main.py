from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import socket
import traceback
from aiohttp import web

# ==================== VERIFICAÇÃO DE INSTÂNCIA ÚNICA ====================
def verificar_instancia_unica():
    try:
        if sys.platform == "win32":
            import win32event, win32api, winerror
            mutex_name = "Bot_WaveX_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_wavex_unico')
            return True
    except Exception:
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.keep_alive = None

bot = MeuBot()

# ==================== KEEP-ALIVE SERVER (PORTA 10000) ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
        self.bot = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request):
                return web.Response(
                    text=f"✅ Bot ONLINE - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    content_type='text/plain'
                )
            
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": self.bot.user.name if self.bot and self.bot.user else "Conectando..."
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Porta 10000
            port = int(os.environ.get('PORT', 10000))
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            print(f"🌐 Keep-alive rodando na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro no servidor: {e}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def set_bot(self, bot):
        self.bot = bot

# Criar instância do keep-alive
keep_alive = KeepAliveServer()

# ==================== EVENTO: DAR CARGO VISITANTE E MENSAGEM DE BOAS-VINDAS ====================
@bot.event
async def on_member_join(member):
    """Quando alguém entra no servidor, dá o cargo 𝐕𝐢𝐬𝐢𝐭𝐚𝐧𝐭𝐞 e envia mensagem no canal 🚪entrada"""
    try:
        # 1. DAR CARGO VISITANTE
        cargo_visitante = discord.utils.get(member.guild.roles, name="𝐕𝐢𝐬𝐢𝐭𝐚𝐧𝐭𝐞")
        
        if cargo_visitante:
            await member.add_roles(cargo_visitante)
            print(f"✅ Cargo 𝐕𝐢𝐬𝐢𝐭𝐚𝐧𝐭𝐞 dado para {member.name}")
        else:
            print(f"⚠️ Cargo 𝐕𝐢𝐬𝐢𝐭𝐚𝐧𝐭𝐞 não encontrado no servidor {member.guild.name}")
        
        # 2. ENVIAR MENSAGEM DE BOAS-VINDAS NO CANAL 🚪entrada
        canal_entrada = discord.utils.get(member.guild.text_channels, name="🚪entrada")
        
        if canal_entrada:
            # Criar embed com a foto do usuário
            embed = discord.Embed(
                description=(
                    f"## 👋 Bem-vindo(a), {member.mention}!\n"
                    f"Seja muito bem-vindo(a) ao **ISRAEL** 💸🔫🇮🇱!\n\n"
                    f"**👤 Total de membros:** {member.guild.member_count}\n\n"
                    f"**💡 Para fazer seu set:**\n"
                    f"> 1. Vá para <#pedir-set> ou <#𝐏𝐞𝐝𝐢𝐫-𝐬𝐞𝐭!>\n"
                    f"> 2. Clique em **'Peça seu Set!'**\n"
                    f"> 3. Digite seu **ID do FiveM**\n"
                    f"> 4. Aguarde aprovação da staff!\n\n"
                    f"Seja Bem-vindo! Esperamos que goste!"
                ),
                color=discord.Color.purple()
            )
            
            # Adicionar thumbnail com a foto do usuário (mini foto)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Adicionar imagem opcional (a que você mencionou)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1462123097627820348/1485738959760920696/07F15636-DD7A-40CD-8257-703F7254123F.png")
            
            embed.set_footer(text=f"ID: {member.id} | Entrou em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            await canal_entrada.send(embed=embed)
            print(f"✅ Mensagem de boas-vindas enviada para {member.name} no canal 🚪entrada")
        else:
            print(f"⚠️ Canal 🚪entrada não encontrado no servidor {member.guild.name}")
            
            # Tentar enviar em algum canal alternativo
            for channel in member.guild.text_channels:
                if channel.permissions_for(member.guild.me).send_messages:
                    embed = discord.Embed(
                        description=(
                            f"## 👋 Bem-vindo(a), {member.mention}!\n"
                            f"Seja muito bem-vindo(a) ao **ISRAEL** 💸🔫🇮🇱!\n\n"
                            f"**👤 Total de membros:** {member.guild.member_count}\n\n"
                            f"**💡 Para fazer seu set:**\n"
                            f"> 1. Vá para <#pedir-set>\n"
                            f"> 2. Clique em **'Peça seu Set!'**\n"
                            f"> 3. Digite seu **ID do FiveM**\n"
                            f"> 4. Aguarde aprovação da staff!\n\n"
                            f"Seja Bem-vindo! Esperamos que goste!"
                        ),
                        color=discord.Color.purple()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    await channel.send(embed=embed)
                    break
                    
    except discord.Forbidden:
        print(f"❌ Sem permissão para dar cargo em {member.guild.name}")
    except Exception as e:
        print(f"❌ Erro ao processar entrada de {member.name}: {e}")

# ==================== COMANDO HELP ====================
@bot.command(name="help")
async def help_command(ctx):
    """!help - Mostra todos os comandos"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot - ISRAEL",
        description="Lista de todos os comandos disponíveis:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📌 Comandos Gerais",
        value="`!help` - Mostra esta mensagem\n"
              "`!ping` - Verifica latência\n"
              "`!status` - Status do bot\n"
              "`!info` - Informações do servidor",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Sistema de Set",
        value="`!setup_set` - Configurar painel de set (ADMIN)\n"
              "`!check_id <id>` - Verifica se ID já está em uso\n"
              "`!sets_pendentes` - Mostra pedidos pendentes\n"
              "`!remover_visitante <@user>` - Remove cargo visitante",
        inline=False
    )
    
    embed.add_field(
        name="🎫 Sistema de Tickets",
        value="`!setup_tickets` - Configurar painel de tickets (ADMIN)",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Sistema de Cargos",
        value="`!setup_cargos` - Configurar painel de cargos (ADMIN)\n"
              "`!fixnick [@user]` - Corrige nickname do usuário",
        inline=False
    )
    
    embed.set_footer(text="ISRAEL • Use os comandos com responsabilidade")
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    """!ping - Verifica latência"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! `{latency}ms`")

@bot.command(name="status")
async def status_command(ctx):
    """!status - Status do bot"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info_command(ctx):
    """!info - Informações do servidor"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title=f"📋 Informações - {guild.name}",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="👑 Dono", value=guild.owner.mention, inline=True)
    embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="💬 Canais", value=len(guild.channels), inline=True)
    embed.add_field(name="🎭 Cargos", value=len(guild.roles), inline=True)
    embed.add_field(name="🚀 Boosters", value=guild.premium_subscription_count or 0, inline=True)
    
    await ctx.send(embed=embed)

# ==================== EVENTO DE READY ====================
@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ BOT CONECTADO!")
    print("="*60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print("="*60)
    
    print("\n📋 Servidores conectados:")
    for i, guild in enumerate(bot.guilds, 1):
        print(f"   {i}. {guild.name} - {guild.member_count} membros")
    
    # Status personalizado
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(bot.guilds)} servidores | !help"
        )
    )
    
    print("\n🚀 BOT PRONTO!")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    print(f"\n📥 Entrou no servidor: {guild.name}")
    
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description="Use **!help** para ver todos os comandos!\n\n"
                          "**Comandos importantes:**\n"
                          "• `!setup_set` - Configurar painel de set\n"
                          "• `!setup_tickets` - Configurar painel de tickets\n"
                          "• `!setup_cargos` - Configurar painel de cargos",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!")
    else:
        await ctx.send(f"❌ Erro: {error}")

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    modulos = [
        'modules.cargos',
        'modules.sets',
        'modules.tickets',
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except Exception as e:
            print(f"   ⚠️ {modulo}: {e}")

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD - ISRAEL")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        print("Configure a variável de ambiente DISCORD_TOKEN")
        sys.exit(1)
    
    # Configurar keep-alive com o bot
    keep_alive.set_bot(bot)
    bot.keep_alive = keep_alive
    
    # Iniciar keep-alive (porta 10000)
    try:
        print("\n🌐 Iniciando servidor keep-alive na porta 10000...")
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Carregar módulos
    await carregar_modulos()
    
    # Conectar ao Discord
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado manualmente")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
    finally:
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
