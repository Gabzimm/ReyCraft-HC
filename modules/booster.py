import discord
from discord.ext import commands
from datetime import datetime

# ========== CONFIGURAÇÃO ==========
# ID do canal onde será enviada a mensagem de boost
CANAL_BOOST_ID = 1516395614194372679

# ID do cargo VIP Booster (opcional - se quiser dar um cargo automático)
CARGO_VIP_BOOSTER_ID = 1482825445077553243  # ← COLOQUE O ID DO CARGO VIP BOOSTER AQUI (ou deixe None)

# ========== COG PRINCIPAL ==========
class BoosterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Módulo Booster carregado!")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Detecta quando um usuário ganha ou perde o boost"""
        
        # Verificar se o usuário ganhou boost
        if not before.premium_since and after.premium_since:
            # Usuário começou a boostar!
            await self.enviar_mensagem_boost(after)
        
        # Verificar se o usuário perdeu o boost (opcional)
        elif before.premium_since and not after.premium_since:
            # Usuário removeu o boost
            await self.enviar_mensagem_remove_boost(after)
    
    async def enviar_mensagem_boost(self, member: discord.Member):
        """Envia mensagem quando alguém dá boost"""
        try:
            canal = self.bot.get_channel(CANAL_BOOST_ID)
            
            if not canal:
                print(f"⚠️ Canal de boost não encontrado! ID: {CANAL_BOOST_ID}")
                return
            
            # Contar quantos boosts o servidor tem
            total_boosts = member.guild.premium_subscription_count or 1
            
            # Criar embed
            embed = discord.Embed(
                description=(
                    f"## 🚀 O jogador {member.mention} ajudou o servidor com **{total_boosts} boost(s)** no nosso servidor!\n\n"
                    f"### Agradecemos muito ❤️\n\n"
                    f"**🎉 Você {member.mention} ganhou o VIP Booster!!**"
                ),
                color=discord.Color.magenta()  # Cor roxa para boost
            )
            
            # Adicionar thumbnail com a foto do usuário
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Adicionar imagem de boost (opcional - você pode mudar a URL)
            embed.set_image(url="https://cdn.discordapp.com/attachments/1386344818833363006/1516449103242985653/ChatGPT_Image_16_de_jun._de_2026_15_25_23.png?ex=6a32aec8&is=6a315d48&hm=0e04514d0efaa9b048ba48332a42a712c6f770401b84a057ad479bc7a748e8f5")
            # OU use uma imagem estática:
            # embed.set_image(url="https://i.imgur.com/boost.png")
            
            embed.set_footer(
                text=f"ID: {member.id} | Boost desde {member.premium_since.strftime('%d/%m/%Y %H:%M') if member.premium_since else 'Agora'}"
            )
            
            # Enviar a mensagem
            await canal.send(embed=embed)
            
            # Dar cargo VIP Booster automaticamente (se configurado)
            if CARGO_VIP_BOOSTER_ID:
                cargo = member.guild.get_role(CARGO_VIP_BOOSTER_ID)
                if cargo:
                    try:
                        await member.add_roles(cargo, reason="Usuário deu boost no servidor!")
                        print(f"✅ Cargo VIP Booster dado para {member.name}")
                    except Exception as e:
                        print(f"❌ Erro ao dar cargo VIP: {e}")
            
            print(f"✅ Mensagem de boost enviada para {member.name}")
            
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem de boost: {e}")
    
    async def enviar_mensagem_remove_boost(self, member: discord.Member):
        """Envia mensagem quando alguém remove o boost (opcional)"""
        try:
            canal = self.bot.get_channel(CANAL_BOOST_ID)
            
            if not canal:
                return
            
            embed = discord.Embed(
                description=(
                    f"## 💔 {member.mention} removeu o boost do servidor\n\n"
                    f"Infelizmente perdemos um booster...\n"
                    f"**Ainda temos {member.guild.premium_subscription_count or 0} boost(s)!**"
                ),
                color=discord.Color.greyple()
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await canal.send(embed=embed)
            print(f"✅ Mensagem de remove boost enviada para {member.name}")
            
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem de remove boost: {e}")
    
    @commands.command(name="setar_cargo_booster")
    @commands.has_permissions(administrator=True)
    async def setar_cargo_booster(self, ctx, cargo: discord.Role = None):
        """
        🔧 Define o cargo que será dado automaticamente para quem der boost
        
        Use: !setar_cargo_booster @cargo
        Exemplo: !setar_cargo_booster @VIP Booster
        """
        global CARGO_VIP_BOOSTER_ID
        
        if cargo is None:
            CARGO_VIP_BOOSTER_ID = None
            await ctx.send("❌ Cargo VIP Booster removido! Agora ninguém receberá cargo automático.")
            return
        
        CARGO_VIP_BOOSTER_ID = cargo.id
        await ctx.send(f"✅ Cargo **{cargo.name}** será dado automaticamente para quem der boost!")
        await ctx.message.delete()
    
    @commands.command(name="testar_boost")
    @commands.has_permissions(administrator=True)
    async def testar_boost(self, ctx):
        """
        🧪 Testa o sistema de boost enviando uma mensagem de exemplo
        
        Use: !testar_boost
        """
        await self.enviar_mensagem_boost(ctx.author)
        await ctx.send("✅ Mensagem de boost de teste enviada!")
        await ctx.message.delete()

# ========== SETUP ==========
async def setup(bot):
    await bot.add_cog(BoosterCog(bot))
    print("✅ Sistema de Booster configurado!")
