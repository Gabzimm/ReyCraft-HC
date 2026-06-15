import discord
from discord.ext import commands
from discord import ui
from datetime import datetime
import sys
import os

# Adicionar caminho para importar utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar sistema de memória
from utils.memory import load_all_data, save_all_data

# ========== FUNÇÕES DE LOG (USANDO MEMÓRIA CENTRAL) ==========
def carregar_logs():
    """Carrega os logs salvos da memória central"""
    dados = load_all_data()
    return dados.get("logs_comandos", [])

def salvar_log(log):
    """Salva um novo log na memória central"""
    dados = load_all_data()
    
    if "logs_comandos" not in dados:
        dados["logs_comandos"] = []
    
    dados["logs_comandos"].append(log)
    
    # Manter apenas os últimos 1000 logs
    if len(dados["logs_comandos"]) > 1000:
        dados["logs_comandos"] = dados["logs_comandos"][-1000:]
    
    save_all_data(dados)

def is_owner(member: discord.Member) -> bool:
    """Verifica se o membro tem cargo Owner"""
    if not member:
        return False
    
    # Dono do servidor
    if member.id == member.guild.owner_id:
        return True
    
    # Cargo com "Owner" ou "𝐎𝐰𝐧𝐞𝐫" no nome
    for role in member.roles:
        if "𝐎𝐰𝐧𝐞𝐫" in role.name.lower():
            return True
    
    return False

# ========== COG PRINCIPAL ==========
class LogsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo de Logs carregado!")
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Registra quando um comando é executado com sucesso"""
        
        # Ignorar comandos de log (para não gerar loop)
        if ctx.command.name in ["logs", "limpar_logs", "log_detalhe", "stats_comandos"]:
            return
        
        # Criar registro do comando
        log_entry = {
            "comando": ctx.command.name,
            "usuario": {
                "nome": str(ctx.author),
                "id": ctx.author.id,
                "mention": ctx.author.mention
            },
            "canal": {
                "nome": ctx.channel.name,
                "id": ctx.channel.id,
                "mention": ctx.channel.mention
            },
            "servidor": {
                "nome": ctx.guild.name,
                "id": ctx.guild.id
            },
            "argumentos": str(ctx.args[2:]) if len(ctx.args) > 2 else "",
            "data": datetime.now().isoformat(),
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "status": "SUCESSO"
        }
        
        # Se for comando de limpeza, registrar quantidade
        if ctx.command.name in ["limpar", "clean", "clear"] and len(ctx.args) > 2:
            log_entry["quantidade"] = ctx.args[2]
        
        # Salvar log
        salvar_log(log_entry)
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Registra erros de comando"""
        
        log_entry = {
            "comando": ctx.command.name if ctx.command else "desconhecido",
            "usuario": {
                "nome": str(ctx.author),
                "id": ctx.author.id,
                "mention": ctx.author.mention
            },
            "canal": {
                "nome": ctx.channel.name,
                "id": ctx.channel.id
            },
            "servidor": {
                "nome": ctx.guild.name if ctx.guild else "DM",
                "id": ctx.guild.id if ctx.guild else 0
            },
            "erro": str(error),
            "data": datetime.now().isoformat(),
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "status": "ERRO"
        }
        
        salvar_log(log_entry)
    
    @commands.command(name="logs")
    async def ver_logs(self, ctx, quantidade: int = 10):
        """
        📋 Ver os últimos logs de comandos
        
        **Apenas cargos com 'Owner' podem usar!**
        
        Uso: !logs [quantidade]
        Exemplo: !logs 20
        """
        
        # Verificar se é Owner
        if not is_owner(ctx.author):
            await ctx.send("❌ **Apenas membros com cargo Owner podem ver os logs!**")
            return
        
        # Limitar quantidade
        if quantidade < 1:
            quantidade = 10
        if quantidade > 50:
            quantidade = 50
        
        # Carregar logs
        logs = carregar_logs()
        
        if not logs:
            await ctx.send("📋 Nenhum log encontrado ainda!")
            return
        
        # Pegar os últimos logs
        logs_recentes = logs[-quantidade:]
        logs_recentes.reverse()
        
        # Criar embed
        embed = discord.Embed(
            title="📋 LOGS DE COMANDOS",
            description=f"Últimos {len(logs_recentes)} comandos executados:",
            color=discord.Color.blue()
        )
        
        for log in logs_recentes[:25]:
            comando = log.get("comando", "?")
            usuario = log.get("usuario", {}).get("nome", "?")
            timestamp = log.get("timestamp", "?")
            status = log.get("status", "SUCESSO")
            
            status_emoji = "❌" if status == "ERRO" else "✅"
            
            embed.add_field(
                name=f"{status_emoji} {timestamp}",
                value=f"**Comando:** `!{comando}`\n**Usuário:** {usuario}\n**Canal:** {log.get('canal', {}).get('nome', '?')}",
                inline=False
            )
        
        embed.set_footer(text=f"Total de logs salvos: {len(logs)} | Use !log_detalhe [número] para ver detalhes")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="log_detalhe")
    async def log_detalhe(self, ctx, indice: int = 1):
        """
        🔍 Ver detalhes de um log específico
        
        **Apenas cargos com 'Owner' podem usar!**
        
        Uso: !log_detalhe [número]
        Exemplo: !log_detalhe 1 (último log)
        """
        
        if not is_owner(ctx.author):
            await ctx.send("❌ **Apenas membros com cargo Owner podem ver os logs!**")
            return
        
        logs = carregar_logs()
        
        if not logs:
            await ctx.send("📋 Nenhum log encontrado!")
            return
        
        if indice < 1 or indice > len(logs):
            await ctx.send(f"❌ Índice inválido! Use entre 1 e {len(logs)}")
            return
        
        # Pegar o log (do mais recente para o mais antigo)
        log = logs[-indice]
        
        embed = discord.Embed(
            title=f"📋 DETALHES DO LOG #{indice}",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="📌 Comando", value=f"`!{log.get('comando', '?')}`", inline=True)
        embed.add_field(name="👤 Usuário", value=log.get('usuario', {}).get('mention', '?'), inline=True)
        embed.add_field(name="🆔 ID", value=f"`{log.get('usuario', {}).get('id', '?')}`", inline=True)
        embed.add_field(name="📅 Data/Hora", value=log.get('timestamp', '?'), inline=True)
        embed.add_field(name="💬 Canal", value=f"#{log.get('canal', {}).get('nome', '?')}", inline=True)
        embed.add_field(name="🌐 Servidor", value=log.get('servidor', {}).get('nome', '?'), inline=True)
        
        if log.get('quantidade'):
            embed.add_field(name="🧹 Quantidade", value=f"{log.get('quantidade')} mensagens", inline=True)
        
        if log.get('argumentos'):
            embed.add_field(name="📝 Argumentos", value=f"`{log.get('argumentos')}`", inline=False)
        
        if log.get('erro'):
            embed.add_field(name="❌ Erro", value=f"```{log.get('erro')[:500]}```", inline=False)
        
        embed.set_footer(text=f"Total de logs: {len(logs)}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="limpar_logs")
    async def limpar_logs(self, ctx):
        """
        🗑️ Limpar todos os logs
        
        **Apenas cargos com 'Owner' podem usar!**
        """
        
        if not is_owner(ctx.author):
            await ctx.send("❌ **Apenas membros com cargo Owner podem limpar os logs!**")
            return
        
        # View de confirmação
        embed = discord.Embed(
            title="⚠️ CONFIRMAR LIMPEZA DE LOGS",
            description="Tem certeza que deseja apagar TODOS os logs? Esta ação é irreversível!",
            color=discord.Color.red()
        )
        
        view = ui.View(timeout=30)
        
        btn_confirmar = ui.Button(label="✅ Sim, apagar tudo", style=discord.ButtonStyle.danger, custom_id="confirmar_limpar")
        btn_cancelar = ui.Button(label="❌ Cancelar", style=discord.ButtonStyle.secondary, custom_id="cancelar_limpar")
        
        async def confirmar_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Apenas quem executou pode confirmar!", ephemeral=True)
                return
            
            # Limpar logs na memória
            dados = load_all_data()
            dados["logs_comandos"] = []
            save_all_data(dados)
            
            for item in view.children:
                item.disabled = True
            await interaction.response.edit_message(content="✅ Todos os logs foram apagados!", embed=None, view=view)
        
        async def cancelar_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Apenas quem executou pode cancelar!", ephemeral=True)
                return
            
            for item in view.children:
                item.disabled = True
            await interaction.response.edit_message(content="❌ Operação cancelada.", embed=None, view=view)
        
        btn_confirmar.callback = confirmar_callback
        btn_cancelar.callback = cancelar_callback
        
        view.add_item(btn_confirmar)
        view.add_item(btn_cancelar)
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="stats_comandos")
    async def stats_comandos(self, ctx):
        """
        📊 Estatísticas de comandos mais usados
        
        **Apenas cargos com 'Owner' podem usar!**
        """
        
        if not is_owner(ctx.author):
            await ctx.send("❌ **Apenas membros com cargo Owner podem ver as estatísticas!**")
            return
        
        logs = carregar_logs()
        
        if not logs:
            await ctx.send("📋 Nenhum comando executado ainda!")
            return
        
        # Contar comandos
        comandos = {}
        usuarios = {}
        
        for log in logs:
            cmd = log.get("comando", "desconhecido")
            user = log.get("usuario", {}).get("nome", "?")
            
            comandos[cmd] = comandos.get(cmd, 0) + 1
            usuarios[user] = usuarios.get(user, 0) + 1
        
        # Ordenar
        comandos_ordenados = sorted(comandos.items(), key=lambda x: x[1], reverse=True)
        usuarios_ordenados = sorted(usuarios.items(), key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="📊 ESTATÍSTICAS DE COMANDOS",
            description=f"Total de comandos executados: **{len(logs)}**",
            color=discord.Color.green()
        )
        
        # Comandos mais usados
        top_comandos = "\n".join([f"`!{cmd}` → {qtd} vezes" for cmd, qtd in comandos_ordenados[:10]])
        embed.add_field(name="🔥 Comandos mais usados", value=top_comandos or "Nenhum", inline=False)
        
        # Usuários mais ativos
        top_usuarios = "\n".join([f"**{user}** → {qtd} comandos" for user, qtd in usuarios_ordenados[:5]])
        embed.add_field(name="👥 Usuários mais ativos", value=top_usuarios or "Nenhum", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LogsCog(bot))
    print("✅ Sistema de Logs configurado!")
