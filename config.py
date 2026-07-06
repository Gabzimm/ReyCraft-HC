"""
Configurações centralizadas para o módulo de status do Minecraft.
Todas as constantes e configurações devem ser definidas aqui para facilitar manutenção.
"""

from typing import Final

# ============================================
# CONFIGURAÇÕES DO SERVIDOR MINECRAFT
# ============================================

# Endereço do servidor Minecraft (IP:PORTA ou domínio:porta)
SERVER_ADDRESS: Final[str] = "reycrafthc.enderman.cloud:35089"

# ============================================
# CONFIGURAÇÕES DO DISCORD
# ============================================

# ID do canal onde o painel será exibido
CHANNEL_ID: Final[int] = 1517986127645249760

# ID da mensagem do painel (será preenchido automaticamente na primeira execução)
# Deixe como 0 para criar uma nova mensagem automaticamente
MESSAGE_ID: Final[int] = 0

# ============================================
# INTERVALO DE ATUALIZAÇÃO
# ============================================

# Intervalo em segundos entre cada verificação do servidor
CHECK_INTERVAL: Final[int] = 15

# ============================================
# URL DO BOTÃO
# ============================================

# URL para iniciar o servidor (será usada no botão quando offline)
START_SERVER_URL: Final[str] = "https://freemcserver.net/server/1999797"

# Texto do botão
BUTTON_LABEL: Final[str] = "🚀 Ligar Servidor"

# ============================================
# APARÊNCIA DO EMBED - SERVIDOR ONLINE
# ============================================

TITLE_ONLINE: Final[str] = "🟢 Servidor Online"
COLOR_ONLINE: Final[int] = 0x57F287  # Verde
DESCRIPTION_ONLINE: Final[str] = "O servidor está funcionando normalmente."

# ============================================
# APARÊNCIA DO EMBED - SERVIDOR OFFLINE
# ============================================

TITLE_OFFLINE: Final[str] = "🔴 Servidor Offline"
COLOR_OFFLINE: Final[int] = 0xED4245  # Vermelho
DESCRIPTION_OFFLINE: Final[str] = (
    "> O servidor está indisponível no momento.\n"
    "Clique no botão abaixo para iniciar o servidor."
)

# ============================================
# RODAPÉ DO EMBED
# ============================================

FOOTER_TEXT: Final[str] = "Atualizado automaticamente"
FOOTER_ICON_URL: Final[str] = (
    "https://cdn.discordapp.com/attachments/seu-icone.png"  # Opcional
)

# ============================================
# FORMATO DOS CAMPOS DO EMBED
# ============================================

FIELD_PLAYERS: Final[str] = "👥 Jogadores"
FIELD_VERSION: Final[str] = "📦 Versão"
FIELD_UPDATED: Final[str] = "🕒 Atualizado"

# ============================================
# TIMEOUT DE CONEXÃO
# ============================================

# Timeout em segundos para consulta ao servidor Minecraft
CONNECTION_TIMEOUT: Final[int] = 5

# ============================================
# MENSAGENS DE LOG
# ============================================

LOG_PREFIX: Final[str] = "[Minecraft Status]"
LOG_ONLINE: Final[str] = "Servidor está ONLINE"
LOG_OFFLINE: Final[str] = "Servidor está OFFLINE"
LOG_ERROR: Final[str] = "Erro ao consultar servidor"
LOG_PANEL_CREATED: Final[str] = "Painel criado com sucesso"
LOG_PANEL_UPDATED: Final[str] = "Painel atualizado"
