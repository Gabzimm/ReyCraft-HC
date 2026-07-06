"""
Componentes de interface para o painel de status do Minecraft.
Contém a criação de embeds e views (botões).
"""

import discord
from datetime import datetime, timezone
from typing import Optional

# Importa as configurações
from config import (
    START_SERVER_URL,
    BUTTON_LABEL,
    TITLE_ONLINE,
    TITLE_OFFLINE,
    COLOR_ONLINE,
    COLOR_OFFLINE,
    DESCRIPTION_ONLINE,
    DESCRIPTION_OFFLINE,
    FOOTER_TEXT,
    FOOTER_ICON_URL,
    FIELD_PLAYERS,
    FIELD_VERSION,
    FIELD_UPDATED,
)


def create_status_embed(
    is_online: bool,
    players_online: Optional[int] = None,
    max_players: Optional[int] = None,
    version: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> discord.Embed:
    """
    Cria o embed do painel de status.

    Args:
        is_online: Indica se o servidor está online
        players_online: Número de jogadores online (None se offline)
        max_players: Número máximo de jogadores (None se offline)
        version: Versão do servidor (None se offline)
        timestamp: Momento da última atualização

    Returns:
        discord.Embed configurado
    """
    if is_online:
        title = TITLE_ONLINE
        color = COLOR_ONLINE
        description = DESCRIPTION_ONLINE
        players_str = f"{players_online} / {max_players}"
        version_str = version or "Desconhecida"
    else:
        title = TITLE_OFFLINE
        color = COLOR_OFFLINE
        description = DESCRIPTION_OFFLINE
        players_str = "0 / —"
        version_str = "—"

    # Cria o embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=timestamp or datetime.now(timezone.utc),
    )

    # Adiciona campos
    embed.add_field(
        name=FIELD_PLAYERS,
        value=players_str,
        inline=True,
    )
    embed.add_field(
        name=FIELD_VERSION,
        value=version_str,
        inline=True,
    )
    embed.add_field(
        name=FIELD_UPDATED,
        value=f"<t:{int((timestamp or datetime.now(timezone.utc)).timestamp())}:R>",
        inline=True,
    )

    # Adiciona rodapé
    embed.set_footer(
        text=FOOTER_TEXT,
        icon_url=FOOTER_ICON_URL if FOOTER_ICON_URL != "https://cdn.discordapp.com/attachments/seu-icone.png" else None,
    )

    return embed


def create_status_view(is_online: bool) -> discord.ui.View:
    """
    Cria a view com botões para o painel de status.

    Args:
        is_online: Indica se o servidor está online

    Returns:
        discord.ui.View configurada
    """
    view = discord.ui.View(timeout=None)

    # Botão para ligar o servidor (visível apenas quando offline)
    if not is_online:
        button = discord.ui.Button(
            label=BUTTON_LABEL,
            url=START_SERVER_URL,
            style=discord.ButtonStyle.link,
        )
        view.add_item(button)

    return view
