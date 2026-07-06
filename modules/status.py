"""
Módulo de status do servidor Minecraft.
Responsável por monitorar e exibir o status do servidor em tempo real.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import discord
from discord.ext import commands
from mcstatus import JavaServer

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
        self.server = JavaServer.lookup(SERVER_ADDRESS, timeout=CONNECTION_TIMEOUT)
        self._task: Optional[asyncio.Task] = None
        self._panel_message: Optional[discord.Message] = None

    async def cog_load(self) -> None:
        """
        Método chamado automaticamente quando a cog é carregada.
        Inicia o loop de atualização do painel.
        """
        logger.info(f"{LOG_PREFIX} Módulo de status carregado")

        # Aguarda o bot estar pronto antes de iniciar
        await self.bot.wait_until_ready()

        # Inicia a task de atualização
        self._task = asyncio.create_task(self._status_loop())
        logger.info(f"{LOG_PREFIX} Loop de atualização iniciado")

    async def cog_unload(self) -> None:
        """
        Método chamado quando a cog é descarregada.
        Cancela o loop de atualização.
        """
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info(f"{LOG_PREFIX} Loop de atualização cancelado")

    async def _get_server_status(self) -> Tuple[bool, Optional[int], Optional[int], Optional[str]]:
        """
        Consulta o status do servidor Minecraft.

        Returns:
            Tupla contendo:
            - is_online: Se o servidor está online
            - players_online: Número de jogadores online
            - max_players: Número máximo de jogadores
            - version: Versão do servidor
        """
        try:
            # Tenta obter o status do servidor
            status = await self.server.async_status()

            players_online = status.players.online
            max_players = status.players.max
            version = status.version.name

            logger.debug(
                f"{LOG_PREFIX} {LOG_ONLINE} - "
                f"Jogadores: {players_online}/{max_players} - "
                f"Versão: {version}"
            )

            return True, players_online, max_players, version

        except Exception as e:
            # Qualquer erro significa que o servidor está offline/inacessível
            logger.warning(f"{LOG_PREFIX} {LOG_ERROR}: {e}")
            return False, None, None, None

    async def _get_or_create_panel_message(self) -> Optional[discord.Message]:
        """
        Obtém a mensagem do painel existente ou cria uma nova.

        Returns:
            Mensagem do painel ou None se não foi possível obter/criar
        """
        try:
            channel = self.bot.get_channel(CHANNEL_ID)
            if not channel:
                logger.error(f"{LOG_PREFIX} Canal {CHANNEL_ID} não encontrado")
                return None

            # Tenta buscar mensagem existente
            if MESSAGE_ID != 0:
                try:
                    message = await channel.fetch_message(MESSAGE_ID)
                    logger.debug(f"{LOG_PREFIX} Mensagem existente encontrada: {MESSAGE_ID}")
                    return message
                except discord.NotFound:
                    logger.warning(f"{LOG_PREFIX} Mensagem {MESSAGE_ID} não encontrada, criando nova")
                except discord.Forbidden:
                    logger.error(f"{LOG_PREFIX} Sem permissão para acessar mensagem {MESSAGE_ID}")
                    return None

            # Cria uma nova mensagem
            embed = create_status_embed(is_online=False)
            view = create_status_view(is_online=False)
            message = await channel.send(embed=embed, view=view)

            logger.info(f"{LOG_PREFIX} {LOG_PANEL_CREATED} - ID: {message.id}")
            logger.warning(
                f"{LOG_PREFIX} Atualize MESSAGE_ID no config.py para {message.id} "
                "para manter o painel após reinicializações"
            )

            return message

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Erro ao obter/criar mensagem do painel: {e}")
            return None

    async def _update_panel(self) -> None:
        """
        Atualiza o painel de status com as informações mais recentes do servidor.
        """
        try:
            # Obtém ou cria a mensagem do painel
            if not self._panel_message:
                self._panel_message = await self._get_or_create_panel_message()
                if not self._panel_message:
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
            logger.debug(
                f"{LOG_PREFIX} {LOG_PANEL_UPDATED} - "
                f"Status: {'Online' if is_online else 'Offline'}"
            )

        except discord.NotFound:
            # Mensagem foi deletada, recriar na próxima iteração
            logger.warning(f"{LOG_PREFIX} Mensagem do painel foi deletada, recriando...")
            self._panel_message = None

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Erro ao atualizar painel: {e}", exc_info=True)

    async def _status_loop(self) -> None:
        """
        Loop principal que atualiza o painel periodicamente.
        Continua executando mesmo se ocorrerem erros.
        """
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                await self._update_panel()
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Erro inesperado no loop de status: {e}",
                    exc_info=True,
                )

            # Aguarda o intervalo configurado antes da próxima verificação
            await asyncio.sleep(CHECK_INTERVAL)


async def setup(bot: commands.Bot) -> None:
    """
    Função de setup para carregar a cog.

    Args:
        bot: Instância do bot Discord
    """
    await bot.add_cog(MinecraftStatus(bot))
