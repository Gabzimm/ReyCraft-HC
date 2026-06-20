import discord
from discord.ext import commands
from discord import ui, ButtonStyle
import json
from datetime import datetime
import asyncio
from typing import Optional, List

# ========== SISTEMA DE MENSAGENS AVANÇADO ==========

class MessageBuilder:
    """Classe para construir mensagens complexas"""
    def __init__(self):
        self.content = None
        self.embeds = []
        self.components = []
        self.webhook_name = None
        self.webhook_avatar = None
        
    def add_text(self, text: str):
        self.content = text
        return self
        
    def add_embed(self, title: str = None, description: str = None, color: str = "#7289da"):
        embed_data = {
            "title": title,
            "description": description,
            "color": int(color.replace("#", ""), 16) if color else 0x7289da,
            "fields": [],
            "author": None,
            "thumbnail": None,
            "image": None,
            "footer_text": None,  # Mudado: separado
            "footer_icon": None,  # Mudado: separado
            "timestamp": False
        }
        self.embeds.append(embed_data)
        return len(self.embeds) - 1
        
    def add_field(self, embed_index: int, name: str, value: str, inline: bool = True):
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["fields"].append({
                "name": name,
                "value": value,
                "inline": inline
            })
        return self
        
    def set_author(self, embed_index: int, name: str, icon_url: str = None, url: str = None):
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["author"] = {
                "name": name,
                "icon_url": icon_url,
                "url": url
            }
        return self
        
    def set_thumbnail(self, embed_index: int, url: str):
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["thumbnail"] = url
        return self
        
    def set_image(self, embed_index: int, url: str):
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["image"] = url
        return self
        
    def set_footer(self, embed_index: int, text: str, icon_url: str = None):
        """Define o footer - AGORA FUNCIONA COM ÍCONE"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["footer_text"] = text
            self.embeds[embed_index]["footer_icon"] = icon_url
        return self
        
    def set_timestamp(self, embed_index: int, enabled: bool = True):
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["timestamp"] = enabled
        return self
        
    def add_link_button(self, label: str, url: str, emoji: str = None, row: int = 0):
        button_data = {
            "label": label,
            "url": url,
            "emoji": emoji,
            "row": row,
            "type": "link"
        }
        self.components.append(button_data)
        return self
        
    def build_embeds(self) -> Optional[List[discord.Embed]]:
        """Constrói os embeds do Discord - CORRIGIDO"""
        if not self.embeds:
            return None
            
        embeds = []
        for embed_data in self.embeds:
            embed = discord.Embed(
                title=embed_data.get("title"),
                description=embed_data.get("description"),
                color=embed_data.get("color", 0x7289da)
            )
            
            # Fields
            for field in embed_data.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
            
            # Author (com ícone - FUNCIONA)
            if embed_data.get("author"):
                author = embed_data["author"]
                embed.set_author(
                    name=author.get("name", ""),
                    icon_url=author.get("icon_url"),
                    url=author.get("url")
                )
            
            # Thumbnail (FUNCIONA)
            if embed_data.get("thumbnail"):
                try:
                    embed.set_thumbnail(url=embed_data["thumbnail"])
                except:
                    pass
            
            # Imagem principal (FUNCIONA)
            if embed_data.get("image"):
                try:
                    embed.set_image(url=embed_data["image"])
                except:
                    pass
            
            # Footer - CORRIGIDO (AGORA COM ÍCONE)
            footer_text = embed_data.get("footer_text")
            footer_icon = embed_data.get("footer_icon")
            
            if footer_text or footer_icon:
                # O Discord.py aceita icon_url no set_footer SIM!
                embed.set_footer(
                    text=footer_text or "",
                    icon_url=footer_icon
                )
            
            # Timestamp
            if embed_data.get("timestamp"):
                embed.timestamp = datetime.now()
            
            embeds.append(embed)
        
        return embeds
        
    def build_view(self) -> Optional[ui.View]:
        """Constrói a view com botões"""
        if not self.components:
            return None
            
        view = ui.View(timeout=None)
        
        for button_data in self.components:
            if button_data.get("type") == "link":
                button = ui.Button(
                    label=button_data.get("label", ""),
                    style=ButtonStyle.link,
                    url=button_data.get("url"),
                    emoji=button_data.get("emoji"),
                    row=button_data.get("row", 0)
                )
                view.add_item(button)
        
        return view


# ========== MODALS ==========

class TextMessageModal(ui.Modal):
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📝 Adicionar Texto")
        self.builder = builder
        
        self.texto = ui.TextInput(
            label="Texto da Mensagem",
            placeholder="Digite o texto...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.texto)
        
    async def on_submit(self, interaction: discord.Interaction):
        self.builder.add_text(self.texto.value)
        await interaction.response.send_message("✅ Texto adicionado!", ephemeral=True)


class EmbedBasicModal(ui.Modal):
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📊 Criar Painel (Embed)")
        self.builder = builder
        
        self.titulo = ui.TextInput(label="Título do Painel", placeholder="Título principal...", max_length=256, required=False)
        self.add_item(self.titulo)
        
        self.descricao = ui.TextInput(label="Descrição", placeholder="Conteúdo do painel...", style=discord.TextStyle.paragraph, max_length=4000, required=True)
        self.add_item(self.descricao)
        
        self.cor = ui.TextInput(label="Cor (Hex)", placeholder="#7289da", max_length=7, required=False)
        self.add_item(self.cor)
        
    async def on_submit(self, interaction: discord.Interaction):
        title = self.titulo.value or None
        description = self.descricao.value
        color = self.cor.value or "#7289da"
        self.builder.add_embed(title=title, description=description, color=color)
        await interaction.response.send_message("✅ Painel criado!", ephemeral=True)


class EmbedFieldModal(ui.Modal):
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="📋 Adicionar Campo")
        self.builder = builder
        self.embed_index = embed_index
        
        self.nome = ui.TextInput(label="Nome do Campo", placeholder="Título...", max_length=256, required=True)
        self.add_item(self.nome)
        
        self.valor = ui.TextInput(label="Valor do Campo", placeholder="Conteúdo...", style=discord.TextStyle.paragraph, max_length=1024, required=True)
        self.add_item(self.valor)
        
        self.inline_input = ui.TextInput(label="Em linha? (sim/não)", placeholder="sim", max_length=3, required=False)
        self.add_item(self.inline_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        inline = self.inline_input.value.lower() == "sim" if self.inline_input.value else True
        self.builder.add_field(self.embed_index, self.nome.value, self.valor.value, inline)
        await interaction.response.send_message("✅ Campo adicionado!", ephemeral=True)


class EmbedFooterModal(ui.Modal):
    """Modal para footer COM ÍCONE (AGORA FUNCIONA)"""
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="🔗 Adicionar Footer com Ícone")
        self.builder = builder
        self.embed_index = embed_index
        
        self.texto_footer = ui.TextInput(
            label="Texto do Footer",
            placeholder="Texto do rodapé...",
            style=discord.TextStyle.paragraph,
            max_length=2048,
            required=True
        )
        self.add_item(self.texto_footer)
        
        self.url_icone = ui.TextInput(
            label="URL do Ícone do Footer",
            placeholder="https://exemplo.com/icone.png (URL direta da imagem)",
            required=False
        )
        self.add_item(self.url_icone)
        
    async def on_submit(self, interaction: discord.Interaction):
        text = self.texto_footer.value
        icon_url = self.url_icone.value if self.url_icone.value else None
        self.builder.set_footer(self.embed_index, text, icon_url)
        await interaction.response.send_message("✅ Footer adicionado!", ephemeral=True)


class ButtonLinkModal(ui.Modal):
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="🔗 Adicionar Botão com Link")
        self.builder = builder
        
        self.label_btn = ui.TextInput(label="Texto do Botão", placeholder="Ex: Acessar Site", max_length=80, required=True)
        self.add_item(self.label_btn)
        
        self.url_btn = ui.TextInput(label="URL do Link", placeholder="https://...", max_length=2000, required=True)
        self.add_item(self.url_btn)
        
        self.emoji_btn = ui.TextInput(label="Emoji (opcional)", placeholder="😊", max_length=100, required=False)
        self.add_item(self.emoji_btn)
        
        self.linha_btn = ui.TextInput(label="Linha (0-4)", placeholder="0", max_length=1, required=False)
        self.add_item(self.linha_btn)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            row = int(self.linha_btn.value) if self.linha_btn.value else 0
        except:
            row = 0
        self.builder.add_link_button(
            label=self.label_btn.value,
            url=self.url_btn.value,
            emoji=self.emoji_btn.value or None,
            row=min(row, 4)
        )
        await interaction.response.send_message("✅ Botão adicionado!", ephemeral=True)


class EmbedAuthorModal(ui.Modal):
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="👤 Adicionar Autor")
        self.builder = builder
        self.embed_index = embed_index
        
        self.nome_autor = ui.TextInput(label="Nome do Autor", placeholder="Nome no topo...", max_length=256, required=True)
        self.add_item(self.nome_autor)
        
        self.icone_autor = ui.TextInput(label="URL do Ícone", placeholder="https://... (imagem do autor)", required=False)
        self.add_item(self.icone_autor)
        
        self.link_autor = ui.TextInput(label="URL do Link", placeholder="Link ao clicar...", required=False)
        self.add_item(self.link_autor)
        
    async def on_submit(self, interaction: discord.Interaction):
        self.builder.set_author(
            self.embed_index,
            self.nome_autor.value,
            self.icone_autor.value or None,
            self.link_autor.value or None
        )
        await interaction.response.send_message("✅ Autor adicionado!", ephemeral=True)


class EmbedImageModal(ui.Modal):
    def __init__(self, builder: MessageBuilder, embed_index: int, image_type: str):
        super().__init__(title=f"🖼️ Adicionar {image_type}")
        self.builder = builder
        self.embed_index = embed_index
        self.image_type = image_type
        
        self.url_imagem = ui.TextInput(
            label=f"URL da {image_type}",
            placeholder="https://... (URL direta da imagem)",
            required=True
        )
        self.add_item(self.url_imagem)
        
    async def on_submit(self, interaction: discord.Interaction):
        url = self.url_imagem.value
        if self.image_type == "Thumbnail":
            self.builder.set_thumbnail(self.embed_index, url)
        else:
            self.builder.set_image(self.embed_index, url)
        await interaction.response.send_message(f"✅ {self.image_type} adicionada!", ephemeral=True)


class ChannelSelectModal(ui.Modal):
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📤 Enviar Mensagem")
        self.builder = builder
        
        self.id_canal = ui.TextInput(label="ID do Canal", placeholder="Cole o ID do canal...", max_length=20, required=True)
        self.add_item(self.id_canal)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.id_canal.value)
        except:
            await interaction.response.send_message("❌ ID inválido!", ephemeral=True)
            return
            
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("❌ Canal não encontrado!", ephemeral=True)
            return
        
        try:
            embeds = self.builder.build_embeds()
            view = self.builder.build_view()
            
            await channel.send(
                content=self.builder.content,
                embeds=embeds,
                view=view
            )
            await interaction.response.send_message(f"✅ Mensagem enviada para {channel.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


# ========== VIEW PRINCIPAL ==========

class MessageCreatorView(ui.View):
    def __init__(self, builder: MessageBuilder):
        super().__init__(timeout=600)
        self.builder = builder
        self.current_embed_index = -1
        
    @ui.select(
        placeholder="🎨 Selecione o que adicionar...",
        options=[
            discord.SelectOption(label="📝 Texto Normal", value="text", description="Texto acima dos painéis"),
            discord.SelectOption(label="📊 Criar Painel", value="embed", description="Painel com título e descrição"),
            discord.SelectOption(label="📋 Adicionar Campo", value="field", description="Campos de informação"),
            discord.SelectOption(label="👤 Adicionar Autor", value="author", description="Autor no topo do painel"),
            discord.SelectOption(label="🖼️ Thumbnail", value="thumbnail", description="Imagem pequena no canto"),
            discord.SelectOption(label="🖼️ Imagem Principal", value="image", description="Imagem grande no painel"),
            discord.SelectOption(label="🔗 Footer com Ícone", value="footer", description="Rodapé com ícone FUNCIONANDO"),
            discord.SelectOption(label="🔘 Botão com Link", value="button_link", description="Botão que abre URL"),
            discord.SelectOption(label="👁️ Visualizar", value="preview", description="Ver preview"),
            discord.SelectOption(label="📤 Enviar", value="send", description="Enviar para canal"),
            discord.SelectOption(label="❌ Cancelar", value="cancel", description="Descartar"),
        ]
    )
    async def select_option(self, interaction: discord.Interaction, select: ui.Select):
        option = select.values[0]
        
        modals = {
            "text": TextMessageModal,
            "embed": EmbedBasicModal,
            "field": EmbedFieldModal,
            "author": EmbedAuthorModal,
            "thumbnail": EmbedImageModal,
            "image": EmbedImageModal,
            "footer": EmbedFooterModal,
            "button_link": ButtonLinkModal,
            "send": ChannelSelectModal,
        }
        
        if option in ["field", "author", "thumbnail", "image", "footer"]:
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
                
        if option == "preview":
            await self.show_preview(interaction)
            return
        
        if option == "cancel":
            await interaction.response.send_message("❌ Cancelado!", ephemeral=True)
            self.stop()
            return
        
        if option in ["thumbnail", "image"]:
            image_type = "Thumbnail" if option == "thumbnail" else "Imagem Principal"
            modal = EmbedImageModal(self.builder, self.current_embed_index, image_type)
        elif option in ["field", "author", "footer"]:
            modal_class = modals[option]
            modal = modal_class(self.builder, self.current_embed_index)
        elif option in modals:
            modal_class = modals[option]
            modal = modal_class(self.builder)
        else:
            return
        
        if option == "embed":
            self.current_embed_index = len(self.builder.embeds)
        
        await interaction.response.send_modal(modal)
        
        # Atualizar status
        embed = discord.Embed(
            title="🎨 Criador de Mensagens",
            description=self.get_status(),
            color=0x7289da
        )
        await interaction.message.edit(embed=embed, view=self)
        
    def get_status(self):
        status = "**📊 Status:**\n\n"
        status += f"{'✅' if self.builder.content else '❌'} Texto\n"
        status += f"{'✅' if self.builder.embeds else '❌'} Painéis: {len(self.builder.embeds)}\n"
        status += f"{'✅' if self.builder.components else '❌'} Botões: {len(self.builder.components)}\n"
        status += "\n📝 **Selecione abaixo!**"
        return status
        
    async def show_preview(self, interaction: discord.Interaction):
        embeds = self.builder.build_embeds()
        view = self.builder.build_view()
        
        if not self.builder.content and not embeds:
            await interaction.response.send_message("❌ Adicione conteúdo!", ephemeral=True)
            return
            
        try:
            await interaction.response.send_message(
                content=f"👁️ **PREVIEW:**\n{self.builder.content or ''}",
                embeds=embeds,
                view=view,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)


# ========== COG ==========

class MessageSystemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Sistema de Mensagens carregado!")
    
    @commands.command(name="criar_msg", aliases=["msg", "embed"])
    @commands.has_permissions(manage_messages=True)
    async def criar_mensagem(self, ctx):
        """Abre o criador de mensagens avançado"""
        builder = MessageBuilder()
        view = MessageCreatorView(builder)
        
        embed = discord.Embed(
            title="🎨 Criador de Mensagens",
            description=(
                "**Crie mensagens com:**\n"
                "📝 Texto | 📊 Painéis | 📋 Campos\n"
                "👤 Autor com ícone | 🔗 Footer com ícone\n"
                "🖼️ Thumbnail e Imagem | 🔘 Botões\n\n"
                "**Selecione abaixo!**"
            ),
            color=0x7289da
        )
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="msg_rapida")
    @commands.has_permissions(manage_messages=True)
    async def msg_rapida(self, ctx, canal: discord.TextChannel = None):
        """Mensagem rápida de exemplo"""
        if canal is None:
            canal = ctx.channel
            
        builder = MessageBuilder()
        builder.add_text("📢 **Anúncio Importante!**")
        
        builder.add_embed(
            title="🌟 Título do Painel",
            description="Descrição com **markdown** e [links](https://discord.com)",
            color="#ff5500"
        )
        builder.add_field(0, "📌 Campo 1", "Valor 1", True)
        builder.add_field(0, "📌 Campo 2", "Valor 2", True)
        builder.add_field(0, "📌 Campo 3", "Valor 3 largura total", False)
        
        # Footer COM ÍCONE (AGORA FUNCIONA!)
        builder.set_footer(0, "Clique nos botões | WaveX", ctx.author.avatar.url)
        
        # Author com ícone
        builder.set_author(0, ctx.author.name, ctx.author.avatar.url)
        
        # Botões
        builder.add_link_button("🔗 Discord", "https://discord.com")
        builder.add_link_button("🌐 Site", "https://example.com")
        
        embeds = builder.build_embeds()
        view = builder.build_view()
        
        await canal.send(content=builder.content, embeds=embeds, view=view)
        await ctx.send(f"✅ Enviado em {canal.mention}!", delete_after=5)


async def setup(bot):
    await bot.add_cog(MessageSystemCog(bot))
    print("✅ Sistema de Mensagens configurado!")
