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
        self.content = None  # Mensagem de texto normal
        self.embeds = []  # Lista de embeds (painéis)
        self.components = []  # Botões e outros componentes
        self.webhook_name = None
        self.webhook_avatar = None
        
    def add_text(self, text: str):
        """Adiciona texto normal acima dos embeds"""
        self.content = text
        return self
        
    def add_embed(self, title: str = None, description: str = None, color: str = "#7289da"):
        """Adiciona um novo embed (painel)"""
        embed_data = {
            "title": title,
            "description": description,
            "color": int(color.replace("#", ""), 16) if color else 0x7289da,
            "fields": [],
            "author": None,
            "thumbnail": None,
            "image": None,
            "footer": None,
            "timestamp": False
        }
        self.embeds.append(embed_data)
        return len(self.embeds) - 1  # Retorna índice do embed
        
    def add_field(self, embed_index: int, name: str, value: str, inline: bool = True):
        """Adiciona um campo ao embed"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["fields"].append({
                "name": name,
                "value": value,
                "inline": inline
            })
        return self
        
    def set_author(self, embed_index: int, name: str, icon_url: str = None, url: str = None):
        """Define o autor do embed (aparece no topo)"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["author"] = {
                "name": name,
                "icon_url": icon_url,
                "url": url
            }
        return self
        
    def set_thumbnail(self, embed_index: int, url: str):
        """Define thumbnail (imagem pequena no canto)"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["thumbnail"] = url
        return self
        
    def set_image(self, embed_index: int, url: str):
        """Define imagem principal do embed"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["image"] = url
        return self
        
    def set_footer(self, embed_index: int, text: str, icon_url: str = None):
        """Define o footer (rodapé) - CORRIGIDO"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["footer"] = {
                "text": text,
                "icon_url": icon_url
            }
        return self
        
    def set_timestamp(self, embed_index: int, enabled: bool = True):
        """Adiciona timestamp atual no footer"""
        if 0 <= embed_index < len(self.embeds):
            self.embeds[embed_index]["timestamp"] = enabled
        return self
        
    def add_button(self, label: str, style: str = "primary", url: str = None, 
                   custom_id: str = None, emoji: str = None, row: int = 0):
        """Adiciona um botão
        
        Styles: primary, secondary, success, danger, link
        Para botões de link, use url
        Para botões de ação, use custom_id
        """
        styles = {
            "primary": ButtonStyle.primary,
            "secondary": ButtonStyle.secondary,
            "success": ButtonStyle.success,
            "danger": ButtonStyle.danger,
            "link": ButtonStyle.link
        }
        
        button_data = {
            "label": label,
            "style": style,
            "url": url,
            "custom_id": custom_id,
            "emoji": emoji,
            "row": row
        }
        self.components.append(button_data)
        return self
        
    def add_link_button(self, label: str, url: str, emoji: str = None, row: int = 0):
        """Atalho para adicionar botão de link"""
        return self.add_button(label=label, style="link", url=url, emoji=emoji, row=row)
        
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
            
            # Adicionar fields
            for field in embed_data.get("fields", []):
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", True)
                )
            
            # Adicionar author
            if embed_data.get("author"):
                author = embed_data["author"]
                embed.set_author(
                    name=author.get("name", ""),
                    icon_url=author.get("icon_url"),
                    url=author.get("url")
                )
            
            # Adicionar thumbnail - CORRIGIDO
            if embed_data.get("thumbnail"):
                embed.set_thumbnail(url=embed_data["thumbnail"])
            
            # Adicionar imagem principal - CORRIGIDO
            if embed_data.get("image"):
                embed.set_image(url=embed_data["image"])
            
            # Adicionar footer - CORRIGIDO (com suporte a icon_url)
            if embed_data.get("footer"):
                footer_data = embed_data["footer"]
                embed.set_footer(
                    text=footer_data.get("text", ""),
                    icon_url=footer_data.get("icon_url")  # Agora suporta ícone no footer
                )
            
            # Adicionar timestamp
            if embed_data.get("timestamp"):
                embed.timestamp = datetime.now()
            
            embeds.append(embed)
        
        return embeds
        
    def build_view(self) -> Optional[ui.View]:
        """Constrói a view com botões - CORRIGIDO"""
        if not self.components:
            return None
            
        view = ui.View(timeout=None)
        
        for button_data in self.components:
            style_map = {
                "primary": ButtonStyle.primary,
                "secondary": ButtonStyle.secondary,
                "success": ButtonStyle.success,
                "danger": ButtonStyle.danger,
                "link": ButtonStyle.link
            }
            
            style = style_map.get(button_data["style"], ButtonStyle.primary)
            
            if button_data.get("url") and button_data.get("style") == "link":
                # Botão de link
                button = ui.Button(
                    label=button_data.get("label", ""),
                    style=style,
                    url=button_data.get("url"),
                    emoji=button_data.get("emoji"),
                    row=button_data.get("row", 0)
                )
            else:
                # Botão sem ação (placeholder) - EVITA ERRO
                button = ui.Button(
                    label=button_data.get("label", ""),
                    style=style,
                    emoji=button_data.get("emoji"),
                    row=button_data.get("row", 0),
                    disabled=True  # Desabilitado para evitar callback ausente
                )
            
            view.add_item(button)
        
        return view


# ========== MODALS PARA CADA TIPO DE ELEMENTO ==========

class TextMessageModal(ui.Modal):
    """Modal para adicionar texto normal"""
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📝 Adicionar Texto")
        self.builder = builder
        
        self.texto = ui.TextInput(
            label="Texto da Mensagem",
            placeholder="Digite o texto que aparecerá acima dos painéis...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.texto)
        
    async def on_submit(self, interaction: discord.Interaction):
        text = self.texto.value
        self.builder.add_text(text)
        await interaction.response.send_message("✅ Texto adicionado!", ephemeral=True)


class EmbedBasicModal(ui.Modal):
    """Modal para criar embed básico"""
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📊 Criar Painel (Embed)")
        self.builder = builder
        
        self.titulo = ui.TextInput(
            label="Título do Painel",
            placeholder="Título principal (opcional)...",
            max_length=256,
            required=False
        )
        self.add_item(self.titulo)
        
        self.descricao = ui.TextInput(
            label="Descrição",
            placeholder="Conteúdo principal do painel...\nUse \\n para quebrar linha",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=True
        )
        self.add_item(self.descricao)
        
        self.cor = ui.TextInput(
            label="Cor (Hex)",
            placeholder="#7289da (deixe vazio para cor padrão)",
            max_length=7,
            required=False
        )
        self.add_item(self.cor)
        
    async def on_submit(self, interaction: discord.Interaction):
        title = self.titulo.value or None
        description = self.descricao.value
        color = self.cor.value or "#7289da"
        
        self.builder.add_embed(title=title, description=description, color=color)
        await interaction.response.send_message("✅ Painel criado!", ephemeral=True)


class EmbedFieldModal(ui.Modal):
    """Modal para adicionar campos ao embed"""
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="📋 Adicionar Campo")
        self.builder = builder
        self.embed_index = embed_index
        
        self.nome = ui.TextInput(
            label="Nome do Campo",
            placeholder="Título do campo...",
            max_length=256,
            required=True
        )
        self.add_item(self.nome)
        
        self.valor = ui.TextInput(
            label="Valor do Campo",
            placeholder="Conteúdo do campo...",
            style=discord.TextStyle.paragraph,
            max_length=1024,
            required=True
        )
        self.add_item(self.valor)
        
        self.inline_input = ui.TextInput(
            label="Em linha? (sim/não)",
            placeholder="sim",
            max_length=3,
            required=False
        )
        self.add_item(self.inline_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        name = self.nome.value
        value = self.valor.value
        inline = self.inline_input.value.lower() == "sim" if self.inline_input.value else True
        
        self.builder.add_field(self.embed_index, name, value, inline)
        await interaction.response.send_message("✅ Campo adicionado!", ephemeral=True)


class EmbedFooterModal(ui.Modal):
    """Modal para adicionar footer com ícone"""
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="🔗 Adicionar Footer (Rodapé)")
        self.builder = builder
        self.embed_index = embed_index
        
        self.texto_footer = ui.TextInput(
            label="Texto do Footer",
            placeholder="Ex: Clique aqui para acessar\n(links em texto funcionam!)",
            style=discord.TextStyle.paragraph,
            max_length=2048,
            required=True
        )
        self.add_item(self.texto_footer)
        
        self.url_icone = ui.TextInput(
            label="URL do Ícone do Footer (opcional)",
            placeholder="https://exemplo.com/icone.png",
            required=False
        )
        self.add_item(self.url_icone)
        
    async def on_submit(self, interaction: discord.Interaction):
        text = self.texto_footer.value
        icon_url = self.url_icone.value or None
        
        self.builder.set_footer(self.embed_index, text, icon_url)
        await interaction.response.send_message("✅ Footer adicionado!", ephemeral=True)


class ButtonLinkModal(ui.Modal):
    """Modal para adicionar botão de link"""
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="🔗 Adicionar Botão com Link")
        self.builder = builder
        
        self.label_btn = ui.TextInput(
            label="Texto do Botão",
            placeholder="Ex: Acessar Site",
            max_length=80,
            required=True
        )
        self.add_item(self.label_btn)
        
        self.url_btn = ui.TextInput(
            label="URL do Link",
            placeholder="https://...",
            max_length=2000,
            required=True
        )
        self.add_item(self.url_btn)
        
        self.emoji_btn = ui.TextInput(
            label="Emoji (opcional)",
            placeholder="😊 ou :emoji:",
            max_length=100,
            required=False
        )
        self.add_item(self.emoji_btn)
        
        self.linha_btn = ui.TextInput(
            label="Linha (0-4)",
            placeholder="0",
            max_length=1,
            required=False
        )
        self.add_item(self.linha_btn)
        
    async def on_submit(self, interaction: discord.Interaction):
        label = self.label_btn.value
        url = self.url_btn.value
        emoji = self.emoji_btn.value or None
        try:
            row = int(self.linha_btn.value) if self.linha_btn.value else 0
        except:
            row = 0
        
        self.builder.add_link_button(label=label, url=url, emoji=emoji, row=min(row, 4))
        await interaction.response.send_message("✅ Botão de link adicionado!", ephemeral=True)


class EmbedAuthorModal(ui.Modal):
    """Modal para adicionar autor ao embed"""
    def __init__(self, builder: MessageBuilder, embed_index: int):
        super().__init__(title="👤 Adicionar Autor")
        self.builder = builder
        self.embed_index = embed_index
        
        self.nome_autor = ui.TextInput(
            label="Nome do Autor",
            placeholder="Nome que aparecerá no topo...",
            max_length=256,
            required=True
        )
        self.add_item(self.nome_autor)
        
        self.icone_autor = ui.TextInput(
            label="URL do Ícone (opcional)",
            placeholder="https://... (URL da imagem do autor)",
            required=False
        )
        self.add_item(self.icone_autor)
        
        self.link_autor = ui.TextInput(
            label="URL do Link (opcional)",
            placeholder="Link ao clicar no nome do autor...",
            required=False
        )
        self.add_item(self.link_autor)
        
    async def on_submit(self, interaction: discord.Interaction):
        name = self.nome_autor.value
        icon_url = self.icone_autor.value or None
        url = self.link_autor.value or None
        
        self.builder.set_author(self.embed_index, name, icon_url, url)
        await interaction.response.send_message("✅ Autor adicionado!", ephemeral=True)


class EmbedImageModal(ui.Modal):
    """Modal para adicionar imagens"""
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
    """Modal para selecionar canal de envio"""
    def __init__(self, builder: MessageBuilder):
        super().__init__(title="📤 Enviar Mensagem")
        self.builder = builder
        
        self.id_canal = ui.TextInput(
            label="ID do Canal",
            placeholder="Cole o ID do canal de destino...",
            max_length=20,
            required=True
        )
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
            await interaction.response.send_message("❌ Sem permissão para enviar mensagem nesse canal!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao enviar: {str(e)}", ephemeral=True)


# ========== VIEW PRINCIPAL DO CRIADOR ==========

class MessageCreatorView(ui.View):
    def __init__(self, builder: MessageBuilder):
        super().__init__(timeout=600)
        self.builder = builder
        self.current_embed_index = -1
        
    @ui.select(
        placeholder="🎨 Selecione o que adicionar à mensagem...",
        options=[
            discord.SelectOption(label="📝 Texto Normal", value="text", description="Texto acima dos painéis"),
            discord.SelectOption(label="📊 Criar Painel (Embed)", value="embed", description="Painel com título e descrição"),
            discord.SelectOption(label="📋 Adicionar Campo ao Painel", value="field", description="Campos de informação"),
            discord.SelectOption(label="👤 Adicionar Autor", value="author", description="Autor no topo do painel"),
            discord.SelectOption(label="🖼️ Adicionar Thumbnail", value="thumbnail", description="Imagem pequena no canto"),
            discord.SelectOption(label="🖼️ Adicionar Imagem Principal", value="image", description="Imagem grande no painel"),
            discord.SelectOption(label="🔗 Footer com Ícone", value="footer", description="Rodapé com ícone"),
            discord.SelectOption(label="🔘 Botão com Link", value="button_link", description="Botão que abre URL"),
            discord.SelectOption(label="👁️ Visualizar Mensagem", value="preview", description="Ver como ficou"),
            discord.SelectOption(label="📤 Enviar Mensagem", value="send", description="Enviar para um canal"),
            discord.SelectOption(label="❌ Cancelar", value="cancel", description="Descartar tudo"),
        ]
    )
    async def select_option(self, interaction: discord.Interaction, select: ui.Select):
        option = select.values[0]
        
        if option == "text":
            modal = TextMessageModal(self.builder)
            await interaction.response.send_modal(modal)
            
        elif option == "embed":
            modal = EmbedBasicModal(self.builder)
            await interaction.response.send_modal(modal)
            self.current_embed_index = len(self.builder.embeds) - 1 if self.builder.embeds else -1
            
        elif option == "field":
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
            modal = EmbedFieldModal(self.builder, self.current_embed_index)
            await interaction.response.send_modal(modal)
            
        elif option == "author":
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
            modal = EmbedAuthorModal(self.builder, self.current_embed_index)
            await interaction.response.send_modal(modal)
            
        elif option == "thumbnail":
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
            modal = EmbedImageModal(self.builder, self.current_embed_index, "Thumbnail")
            await interaction.response.send_modal(modal)
            
        elif option == "image":
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
            modal = EmbedImageModal(self.builder, self.current_embed_index, "Imagem Principal")
            await interaction.response.send_modal(modal)
            
        elif option == "footer":
            if not self.builder.embeds:
                await interaction.response.send_message("❌ Crie um painel primeiro!", ephemeral=True)
                return
            modal = EmbedFooterModal(self.builder, self.current_embed_index)
            await interaction.response.send_modal(modal)
            
        elif option == "button_link":
            modal = ButtonLinkModal(self.builder)
            await interaction.response.send_modal(modal)
            
        elif option == "preview":
            await self.show_preview(interaction)
            return  # Não atualiza a mensagem
            
        elif option == "send":
            modal = ChannelSelectModal(self.builder)
            await interaction.response.send_modal(modal)
            return  # Não atualiza a mensagem
            
        elif option == "cancel":
            await interaction.response.send_message("❌ Criação cancelada!", ephemeral=True)
            self.stop()
            return
            
        # Atualizar view com informações (apenas se não for preview ou send)
        if option not in ["preview", "send", "cancel"]:
            embed = discord.Embed(
                title="🎨 Criador de Mensagens",
                description=self.get_builder_status(),
                color=0x7289da
            )
            await interaction.message.edit(embed=embed, view=self)
        
    def get_builder_status(self):
        """Retorna status atual do builder"""
        status = "**📊 Status da Mensagem:**\n\n"
        
        if self.builder.content:
            status += "✅ Texto normal adicionado\n"
        else:
            status += "❌ Sem texto normal\n"
            
        if self.builder.embeds:
            status += f"✅ {len(self.builder.embeds)} painel(is) criado(s)\n"
            for i, embed in enumerate(self.builder.embeds):
                status += f"   📊 Painel {i+1}: "
                if embed.get("title"):
                    status += f'"{embed["title"]}"'
                else:
                    status += "Sem título"
                if embed.get("fields"):
                    status += f" ({len(embed['fields'])} campos)"
                if embed.get("footer"):
                    status += " [Footer]"
                if embed.get("author"):
                    status += " [Autor]"
                if embed.get("thumbnail"):
                    status += " [Thumbnail]"
                if embed.get("image"):
                    status += " [Imagem]"
                status += "\n"
        else:
            status += "❌ Nenhum painel criado\n"
            
        if self.builder.components:
            button_count = len(self.builder.components)
            status += f"✅ {button_count} botão(ões) adicionado(s)\n"
        else:
            status += "❌ Nenhum botão adicionado\n"
            
        status += "\n📝 **Selecione abaixo o que adicionar!**"
        return status
        
    async def show_preview(self, interaction: discord.Interaction):
        """Mostra preview da mensagem"""
        embeds = self.builder.build_embeds()
        view = self.builder.build_view()
        
        if not self.builder.content and not embeds:
            await interaction.response.send_message("❌ Adicione conteúdo primeiro!", ephemeral=True)
            return
            
        try:
            # Enviar preview em mensagem privada
            await interaction.response.send_message(
                content=f"👁️ **PREVIEW DA MENSAGEM:**\n{self.builder.content or ''}",
                embeds=embeds,
                view=view,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao mostrar preview: {str(e)}", ephemeral=True)


# ========== COG PRINCIPAL ==========

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
                "**Crie mensagens personalizadas com:**\n"
                "📝 Texto normal\n"
                "📊 Painéis (embeds) com campos\n"
                "👤 Autores com ícones e links\n"
                "🔗 Footer com ícone\n"
                "🖼️ Imagens e thumbnails\n"
                "🔘 Botões com links\n\n"
                "**Selecione abaixo o que deseja adicionar!**"
            ),
            color=0x7289da
        )
        embed.set_footer(text="Selecione as opções para construir sua mensagem")
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="msg_rapida")
    @commands.has_permissions(manage_messages=True)
    async def msg_rapida(self, ctx, canal: discord.TextChannel = None):
        """Cria uma mensagem rápida com texto + botões de link"""
        if canal is None:
            canal = ctx.channel
            
        builder = MessageBuilder()
        
        # Exemplo rápido
        builder.add_text("📢 **Anúncio Importante!**")
        
        builder.add_embed(
            title="🌟 Título do Painel",
            description="Descrição do painel com **markdown** e [links](https://discord.com)",
            color="#ff5500"
        )
        builder.add_field(0, "📌 Campo 1", "Valor do campo 1", True)
        builder.add_field(0, "📌 Campo 2", "Valor do campo 2", True)
        builder.add_field(0, "📌 Campo 3", "Valor do campo 3 largura total", False)
        
        # Footer com ícone (AGORA FUNCIONA!)
        builder.set_footer(0, "Clique nos botões abaixo | Sistema de Mensagens", ctx.author.avatar.url)
        builder.set_author(0, ctx.author.name, ctx.author.avatar.url)
        
        # Botões de link
        builder.add_link_button("🔗 Discord", "https://discord.com", emoji="🔗")
        builder.add_link_button("🌐 Website", "https://example.com", emoji="🌐")
        builder.add_link_button("📚 Documentação", "https://docs.example.com", emoji="📚")
        
        embeds = builder.build_embeds()
        view = builder.build_view()
        
        await canal.send(
            content=builder.content,
            embeds=embeds,
            view=view
        )
        
        await ctx.send(f"✅ Mensagem enviada em {canal.mention}!", delete_after=5)


# ========== SETUP ==========

async def setup(bot):
    await bot.add_cog(MessageSystemCog(bot))
    print("✅ Sistema de Mensagens configurado!")
