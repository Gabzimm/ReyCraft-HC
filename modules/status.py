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
        
        print(f"{LOG_PREFIX} Inicializando módulo...")
        print(f"{LOG_PREFIX} Servidor: {SERVER_ADDRESS}")
        print(f"{LOG_PREFIX} Canal ID: {CHANNEL_ID}")
        print(f"{LOG_PREFIX} Intervalo: {CHECK_INTERVAL}s")

    async def cog_load(self) -> None:
        """
        Método chamado automaticamente quando a cog é carregada.
        """
        print(f"{LOG_PREFIX} cog_load() chamado!")
        
        # Aguarda o bot estar pronto
        print(f"{LOG_PREFIX} Aguardando bot estar pronto...")
        await self.bot.wait_until_ready()
        print(f"{LOG_PREFIX} Bot está pronto! Iniciando status loop...")
        
        # Inicia o loop
        self.status_loop.start()
        print(f"{LOG_PREFIX} Loop iniciado com sucesso!")

    def cog_unload(self) -> None:
        """
        Método chamado quando a cog é descarregada.
        """
        print(f"{LOG_PREFIX} Descarregando módulo...")
        self.status_loop.cancel()

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def status_loop(self):
        """
        Loop que atualiza o painel periodicamente.
        """
        try:
            print(f"{LOG_PREFIX} Executando verificação...")
            await self._update_panel()
        except Exception as e:
            print(f"{LOG_PREFIX} Erro no loop: {e}")
            logger.error(f"Erro no loop: {e}", exc_info=True)

    @status_loop.before_loop
    async def before_status_loop(self):
        """
        Executado antes do loop iniciar.
        Aguarda o bot estar pronto.
        """
        print(f"{LOG_PREFIX} Preparando loop...")
        await self.bot.wait_until_ready()
        print(f"{LOG_PREFIX} Loop preparado!")

    async def _get_server_status(self) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
        """
        Consulta o status do servidor Minecraft.

        Returns:
            Tupla contendo (is_online, players_online, max_players, version)
        """
        try:
            from mcstatus import JavaServer
            
            print(f"{LOG_PREFIX} Consultando servidor {SERVER_ADDRESS}...")
            server = JavaServer.lookup(SERVER_ADDRESS, timeout=CONNECTION_TIMEOUT)
            status = await server.async_status()

            players_online = status.players.online
            max_players = status.players.max
            version = status.version.name

            print(f"{LOG_PREFIX} {LOG_ONLINE} - Jogadores: {players_online}/{max_players} - Versão: {version}")
            return True, players_online, max_players, version

        except Exception as e:
            print(f"{LOG_PREFIX} {LOG_ERROR}: {e}")
            return False, None, None, None

    async def _get_or_create_panel_message(self) -> Optional[discord.Message]:
        """
        Obtém a mensagem do painel existente ou cria uma nova.
        """
        try:
            channel = self.bot.get_channel(CHANNEL_ID)
            
            if not channel:
                print(f"{LOG_PREFIX} ❌ Canal {CHANNEL_ID} não encontrado!")
                # Lista canais disponíveis
                print(f"{LOG_PREFIX} Canais disponíveis:")
                for guild in self.bot.guilds:
                    for ch in guild.channels:
                        if isinstance(ch, discord.TextChannel):
                            print(f"   - {ch.name}: {ch.id}")
                return None

            print(f"{LOG_PREFIX} ✅ Canal encontrado: {channel.name}")

            # Tenta buscar mensagem existente
            if MESSAGE_ID != 0:
                try:
                    message = await channel.fetch_message(MESSAGE_ID)
                    print(f"{LOG_PREFIX} Mensagem existente encontrada: {MESSAGE_ID}")
                    return message
                except discord.NotFound:
                    print(f"{LOG_PREFIX} Mensagem {MESSAGE_ID} não encontrada, criando nova...")
                except Exception as e:
                    print(f"{LOG_PREFIX} Erro ao buscar mensagem: {e}")

            # Cria nova mensagem
            print(f"{LOG_PREFIX} Criando novo painel...")
            embed = create_status_embed(is_online=False)
            view = create_status_view(is_online=False)
            message = await channel.send(embed=embed, view=view)

            print(f"{LOG_PREFIX} {LOG_PANEL_CREATED} - ID: {message.id}")
            print(f"{LOG_PREFIX} ⚠️ Atualize MESSAGE_ID no config.py para: {message.id}")

            return message

        except discord.Forbidden:
            print(f"{LOG_PREFIX} ❌ Sem permissão para enviar mensagens no canal!")
        except Exception as e:
            print(f"{LOG_PREFIX} ❌ Erro ao criar painel: {e}")
            logger.error(f"Erro ao criar painel: {e}", exc_info=True)
        
        return None

    async def _update_panel(self) -> None:
        """
        Atualiza o painel de status com as informações mais recentes.
        """
        try:
            # Obtém ou cria a mensagem do painel
            if not self._panel_message:
                self._panel_message = await self._get_or_create_panel_message()
                if not self._panel_message:
                    print(f"{LOG_PREFIX} ❌ Não foi possível obter/criar painel")
                    return

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
            print(f"{LOG_PREFIX} {LOG_PANEL_UPDATED} - Status: {'Online' if is_online else 'Offline'}")

        except discord.NotFound:
            print(f"{LOG_PREFIX} Mensagem deletada, recriando...")
            self._panel_message = None
        except Exception as e:
            print(f"{LOG_PREFIX} Erro ao atualizar: {e}")
            logger.error(f"Erro ao atualizar: {e}", exc_info=True)


async def setup(bot: commands.Bot) -> None:
    """
    Função de setup para carregar a cog.
    """
    print(f"{LOG_PREFIX} setup() chamado - criando cog...")
    await bot.add_cog(MinecraftStatus(bot))
    print(f"{LOG_PREFIX} Cog adicionada com sucesso!")
