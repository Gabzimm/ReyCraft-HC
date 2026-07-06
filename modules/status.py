"""
Módulo de status do servidor Minecraft.
Responsável por monitorar e exibir o status do servidor em tempo real.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import discord
from discord.ext import commands, tasks

# Importa as configurações
from config import (
    SERVER_ADDRESS,
    CHECK_INTERVAL,
    CHANNEL_ID,
    MESSAGE_ID,
    CONNECTION_TIMEOUT,
    LOG_PREFIX,
    LOG_ONLINE,
    LOG_OFFLINE,
    LOG_ERROR,
    LOG_PANEL_CREATED,
    LOG_PANEL_UPDATED,
)

# Importa os componentes de view
from views.status_view import create_status_embed, create_status_view

# Configuração do logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MinecraftStatus(commands.Cog):
    """
    Cog responsável por gerenciar o painel de status do servidor Minecraft.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """
        Inicializa o módulo de status.

        Args:
            bot: Instância do bot Discord
        """
        self.bot = bot
        self._panel_message: Optional[discord.Message] = None
        
        print(f"{LOG_PREFIX} ╔══════════════════════════════════════╗")
        print(f"{LOG_PREFIX} ║     MÓDULO DE STATUS INICIALIZADO    ║")
        print(f"{LOG_PREFIX} ╚══════════════════════════════════════╝")
        print(f"{LOG_PREFIX} 📡 Servidor: {SERVER_ADDRESS}")
        print(f"{LOG_PREFIX} 📺 Canal ID: {CHANNEL_ID}")
        print(f"{LOG_PREFIX} ⏱️  Intervalo: {CHECK_INTERVAL}s")
        print(f"{LOG_PREFIX} 📝 Message ID: {MESSAGE_ID}")

    async def cog_load(self) -> None:
        """
        Método chamado automaticamente quando a cog é carregada.
        """
        print(f"{LOG_PREFIX} 🔄 cog_load() executado!")
        
        # Aguarda o bot estar pronto
        print(f"{LOG_PREFIX} ⏳ Aguardando bot ficar pronto...")
        await self.bot.wait_until_ready()
        print(f"{LOG_PREFIX} ✅ Bot está pronto!")
        
        # Inicia o loop automático
        print(f"{LOG_PREFIX} 🚀 Iniciando loop automático...")
        self.status_loop.start()
        print(f"{LOG_PREFIX} ✅ Loop automático iniciado!")

    def cog_unload(self) -> None:
        """
        Método chamado quando a cog é descarregada.
        """
        print(f"{LOG_PREFIX} 🛑 Descarregando módulo...")
        self.status_loop.cancel()
        print(f"{LOG_PREFIX} ✅ Módulo descarregado!")

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def status_loop(self):
        """
        Loop que atualiza o painel automaticamente.
        """
        try:
            print(f"{LOG_PREFIX} 🔄 Atualizando painel...")
            await self._update_panel()
            print(f"{LOG_PREFIX} ✅ Painel atualizado!")
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Erro no loop: {e}")
            logger.error(f"Erro no loop: {e}", exc_info=True)

    @status_loop.before_loop
    async def before_status_loop(self):
        """
        Executado antes do loop iniciar.
        Aguarda o bot estar pronto.
        """
        print(f"{LOG_PREFIX} ⏳ Preparando loop...")
        await self.bot.wait_until_ready()
        print(f"{LOG_PREFIX} ✅ Loop preparado!")

    async def _get_server_status(self) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
        """
        Consulta o status do servidor Minecraft.

        Returns:
            Tupla contendo (is_online, players_online, max_players, version)
        """
        try:
            from mcstatus import JavaServer
            
            print(f"{LOG_PREFIX} 🔍 Consultando servidor {SERVER_ADDRESS}...")
            server = JavaServer.lookup(SERVER_ADDRESS, timeout=CONNECTION_TIMEOUT)
            status = await server.async_status()

            players_online = status.players.online
            max_players = status.players.max
            version = status.version.name
            latency = status.latency

            print(f"{LOG_PREFIX} {LOG_ONLINE}")
            print(f"{LOG_PREFIX}    👥 Jogadores: {players_online}/{max_players}")
            print(f"{LOG_PREFIX}    📦 Versão: {version}")
            print(f"{LOG_PREFIX}    📶 Ping: {latency:.0f}ms")
            
            return True, players_online, max_players, version

        except Exception as e:
            print(f"{LOG_PREFIX} {LOG_ERROR}: {type(e).__name__} - {e}")
            return False, None, None, None

    async def _get_or_create_panel_message(self) -> Optional[discord.Message]:
        """
        Obtém a mensagem do painel existente ou cria uma nova.
        """
        try:
            print(f"{LOG_PREFIX} 📺 Procurando canal {CHANNEL_ID}...")
            channel = self.bot.get_channel(CHANNEL_ID)
            
            if not channel:
                print(f"{LOG_PREFIX} ❌ Canal {CHANNEL_ID} não encontrado!")
                
                # Lista canais disponíveis para debug
                print(f"{LOG_PREFIX} 📋 Canais disponíveis:")
                for guild in self.bot.guilds:
                    print(f"{LOG_PREFIX}    Servidor: {guild.name}")
                    for ch in guild.channels:
                        if isinstance(ch, discord.TextChannel):
                            perms = ch.permissions_for(guild.me)
                            if perms.send_messages:
                                print(f"{LOG_PREFIX}       ✅ #{ch.name} (ID: {ch.id})")
                            else:
                                print(f"{LOG_PREFIX}       ❌ #{ch.name} (ID: {ch.id}) - Sem permissão")
                return None

            # Verifica permissões
            perms = channel.permissions_for(channel.guild.me)
            if not perms.send_messages:
                print(f"{LOG_PREFIX} ❌ Sem permissão para enviar mensagens no canal #{channel.name}")
                return None
            if not perms.embed_links:
                print(f"{LOG_PREFIX} ❌ Sem permissão para embeds no canal #{channel.name}")
                return None

            print(f"{LOG_PREFIX} ✅ Canal encontrado: #{channel.name}")
            print(f"{LOG_PREFIX}    Permissões: Send={perms.send_messages}, Embed={perms.embed_links}")

            # Tenta buscar mensagem existente
            if MESSAGE_ID != 0:
                try:
                    message = await channel.fetch_message(MESSAGE_ID)
                    print(f"{LOG_PREFIX} 📝 Mensagem existente encontrada! ID: {MESSAGE_ID}")
                    return message
                except discord.NotFound:
                    print(f"{LOG_PREFIX} ⚠️  Mensagem {MESSAGE_ID} não encontrada")
                except discord.Forbidden:
                    print(f"{LOG_PREFIX} ❌ Sem permissão para ler mensagem {MESSAGE_ID}")
                except Exception as e:
                    print(f"{LOG_PREFIX} ❌ Erro ao buscar mensagem: {e}")

            # Cria nova mensagem
            print(f"{LOG_PREFIX} 🆕 Criando novo painel...")
            embed = create_status_embed(is_online=False)
            view = create_status_view(is_online=False)
            message = await channel.send(embed=embed, view=view)

            print(f"{LOG_PREFIX} ✅ {LOG_PANEL_CREATED}")
            print(f"{LOG_PREFIX}    📝 ID da mensagem: {message.id}")
            print(f"{LOG_PREFIX}    📺 Canal: #{channel.name}")
            print(f"{LOG_PREFIX} ╔══════════════════════════════════════════════════════╗")
            print(f"{LOG_PREFIX} ║  ATUALIZE O MESSAGE_ID NO config.py:                ║")
            print(f"{LOG_PREFIX} ║  MESSAGE_ID: Final[int] = {message.id}              ║")
            print(f"{LOG_PREFIX} ╚══════════════════════════════════════════════════════╝")

            return message

        except discord.Forbidden:
            print(f"{LOG_PREFIX} ❌ ERRO: Sem permissão para enviar mensagens!")
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ ERRO ao criar painel: {type(e).__name__} - {e}")
            logger.error(f"Erro ao criar painel: {e}", exc_info=True)
        
        return None

    async def _update_panel(self) -> None:
        """
        Atualiza o painel de status com as informações mais recentes.
        """
        try:
            # Obtém ou cria a mensagem do painel
            if not self._panel_message:
                print(f"{LOG_PREFIX} 📝 Obtendo/criando mensagem do painel...")
                self._panel_message = await self._get_or_create_panel_message()
                if not self._panel_message:
                    print(f"{LOG_PREFIX} ❌ Falha ao obter/criar painel")
                    return
                print(f"{LOG_PREFIX} ✅ Painel pronto!")

            # Consulta o status do servidor
            is_online, players_online, max_players, version = await self._get_server_status()

            # Cria o embed e view atualizados
            timestamp = datetime.now(timezone.utc)
            embed = create_status_embed(
                is_online=is_online,
                players_online=players_online,
                max_players=max_players,
                version=version,
                timestamp=timestamp,
            )
            view = create_status_view(is_online=is_online)

            # Atualiza a mensagem
            await self._panel_message.edit(embed=embed, view=view)
            
            status_text = "🟢 ONLINE" if is_online else "🔴 OFFLINE"
            print(f"{LOG_PREFIX} {LOG_PANEL_UPDATED} - Status: {status_text}")

        except discord.NotFound:
            print(f"{LOG_PREFIX} ⚠️  Mensagem do painel foi deletada! Recriando...")
            self._panel_message = None
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Erro ao atualizar painel: {type(e).__name__} - {e}")
            logger.error(f"Erro ao atualizar: {e}", exc_info=True)

    # ============================================
    # COMANDOS DE DIAGNÓSTICO
    # ============================================

    @commands.command(name="forcarpainel")
    @commands.has_permissions(administrator=True)
    async def forcar_painel(self, ctx: commands.Context):
        """
        Comando para forçar a criação/atualização do painel.
        Uso: !forcarpainel
        """
        print(f"{LOG_PREFIX} 🛠️  Comando !forcarpainel executado por {ctx.author}")
        
        msg = await ctx.send("🔍 **Forçando criação do painel...**")
        
        # Reseta a mensagem do painel
        self._panel_message = None
        
        # Força atualização
        await self._update_panel()
        
        if self._panel_message:
            await msg.edit(content=f"✅ **Painel criado/atualizado com sucesso!**\n📺 Canal: {self._panel_message.channel.mention}\n📝 ID: `{self._panel_message.id}`")
            print(f"{LOG_PREFIX} ✅ Painel forçado com sucesso!")
        else:
            await msg.edit(content="❌ **Falha ao criar painel!**\nVerifique os logs do Render para mais detalhes.")
            print(f"{LOG_PREFIX} ❌ Falha ao forçar painel")

    @commands.command(name="testarminecraft")
    @commands.has_permissions(administrator=True)
    async def testar_minecraft(self, ctx: commands.Context):
        """
        Testa a conexão com o servidor Minecraft.
        Uso: !testarminecraft
        """
        print(f"{LOG_PREFIX} 🛠️  Comando !testarminecraft executado por {ctx.author}")
        
        msg = await ctx.send("🔍 **Testando conexão com o servidor Minecraft...**")
        
        try:
            from mcstatus import JavaServer
            
            server = JavaServer.lookup(SERVER_ADDRESS, timeout=CONNECTION_TIMEOUT)
            status = await server.async_status()
            
            # Pega informações detalhadas
            players_online = status.players.online
            max_players = status.players.max
            version = status.version.name
            protocol = status.version.protocol
            latency = status.latency
            motd = status.motd.parsed if status.motd else "Sem MOTD"
            
            embed = discord.Embed(
                title="✅ Conexão Bem Sucedida!",
                color=0x57F287,
                description=f"**Servidor:** `{SERVER_ADDRESS}`",
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="👥 Jogadores", value=f"{players_online}/{max_players}", inline=True)
            embed.add_field(name="📦 Versão", value=f"{version} (Protocolo {protocol})", inline=True)
            embed.add_field(name="📶 Ping", value=f"{latency:.0f}ms", inline=True)
            embed.add_field(name="📝 MOTD", value=motd, inline=False)
            
            # Tenta pegar lista de jogadores se houver
            if players_online > 0 and hasattr(status, 'players'):
                try:
                    players_list = []
                    if hasattr(status.players, 'sample') and status.players.sample:
                        for player in status.players.sample:
                            players_list.append(f"• {player.name}")
                    
                    if players_list:
                        embed.add_field(
                            name=f"🎮 Jogadores Online ({len(players_list)})",
                            value="\n".join(players_list[:10]) + ("\n..." if len(players_list) > 10 else ""),
                            inline=False
                        )
                except:
                    pass
            
            await msg.edit(content=None, embed=embed)
            print(f"{LOG_PREFIX} ✅ Teste de conexão bem sucedido!")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            embed = discord.Embed(
                title="❌ Falha na Conexão",
                color=0xED4245,
                description=f"**Servidor:** `{SERVER_ADDRESS}`\n\n**Erro:** `{error_type}`\n**Mensagem:** {error_msg}",
                timestamp=datetime.now(timezone.utc)
            )
            
            # Sugestões baseadas no tipo de erro
            sugestoes = []
            if "ConnectionRefusedError" in error_type or "Connection refused" in error_msg:
                sugestoes.append("• Servidor pode estar offline")
                sugestoes.append("• Porta pode estar errada")
            elif "timeout" in error_msg.lower():
                sugestoes.append("• Servidor não respondeu a tempo")
                sugestoes.append("• Verifique se o IP está correto")
            elif "NameResolutionError" in error_type or "getaddrinfo" in error_msg:
                sugestoes.append("• Domínio/IP não encontrado")
                sugestoes.append("• Verifique o endereço do servidor")
            
            if sugestoes:
                embed.add_field(name="💡 Possíveis Soluções", value="\n".join(sugestoes), inline=False)
            
            await msg.edit(content=None, embed=embed)
            print(f"{LOG_PREFIX} ❌ Teste falhou: {error_type} - {error_msg}")

    @commands.command(name="status")
    async def status_manual(self, ctx: commands.Context):
        """
        Mostra o status atual do servidor Minecraft.
        Uso: !status
        """
        print(f"{LOG_PREFIX} Comando !status executado por {ctx.author}")
        
        async with ctx.typing():
            is_online, players, max_p, version = await self._get_server_status()
            
            if is_online:
                embed = discord.Embed(
                    title="🟢 Servidor Online",
                    color=0x57F287,
                    timestamp=datetime.now(timezone.utc)
                )
                embed.add_field(name="👥 Jogadores", value=f"{players}/{max_p}", inline=True)
                embed.add_field(name="📦 Versão", value=version, inline=True)
                embed.set_footer(text="✅ Servidor operacional")
            else:
                embed = discord.Embed(
                    title="🔴 Servidor Offline",
                    color=0xED4245,
                    description="O servidor está indisponível no momento.",
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text="❌ Servidor inacessível")
            
            await ctx.send(embed=embed)

    @commands.command(name="statusinfo")
    @commands.has_permissions(administrator=True)
    async def status_info(self, ctx: commands.Context):
        """
        Mostra informações de diagnóstico do módulo de status.
        Uso: !statusinfo
        """
        print(f"{LOG_PREFIX} Comando !statusinfo executado por {ctx.author}")
        
        embed = discord.Embed(
            title="📊 Diagnóstico do Módulo de Status",
            color=0x3498db,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Informações de configuração
        embed.add_field(name="📡 Servidor", value=f"`{SERVER_ADDRESS}`", inline=False)
        embed.add_field(name="📺 Canal ID", value=f"`{CHANNEL_ID}`", inline=True)
        embed.add_field(name="📝 Message ID", value=f"`{MESSAGE_ID}`", inline=True)
        embed.add_field(name="⏱️ Intervalo", value=f"{CHECK_INTERVAL}s", inline=True)
        
        # Status do painel
        if self._panel_message:
            embed.add_field(
                name="📋 Painel Atual",
                value=f"✅ Ativo\n📺 Canal: {self._panel_message.channel.mention}\n📝 ID: `{self._panel_message.id}`",
                inline=False
            )
        else:
            embed.add_field(name="📋 Painel Atual", value="❌ Não inicializado", inline=False)
        
        # Status do loop
        loop_status = "✅ Rodando" if self.status_loop.is_running() else "❌ Parado"
        embed.add_field(name="🔄 Loop Automático", value=loop_status, inline=True)
        
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """
    Função de setup para carregar a cog.
    """
    print(f"{LOG_PREFIX} 🔧 setup() chamado - registrando cog...")
    await bot.add_cog(MinecraftStatus(bot))
    print(f"{LOG_PREFIX} ✅ Cog registrada com sucesso!")
