// lib/legendquest.js
// Avisa o plugin LegendQuest (rodando no servidor de Minecraft) quando uma
// compra de VIP de clã é confirmada, pra ele aplicar o nível (glowing, bônus
// de kills, partículas etc.) no clã do comprador.
//
// Contrato do plugin (webhook.porta / webhook.token no config.yml dele):
//   POST http://SEU_SERVIDOR:8765/compra
//   Body: { token, uuid, pacote, valor }

async function notificarCompraLegendQuest(uuidJogador, pacote, valor) {
  const MC_WEBHOOK_URL = process.env.MC_WEBHOOK_URL;     // ex: http://123.45.67.89:8765/compra
  const MC_WEBHOOK_TOKEN = process.env.MC_WEBHOOK_TOKEN; // igual ao "webhook.token" do config.yml do plugin

  if (!MC_WEBHOOK_URL || !MC_WEBHOOK_TOKEN) {
    console.warn('LegendQuest: MC_WEBHOOK_URL/MC_WEBHOOK_TOKEN não configurados, pulando notificação.');
    return { ok: false, motivo: 'não configurado' };
  }
  if (!uuidJogador) {
    console.warn('LegendQuest: comprador sem UUID vinculado, não dá pra aplicar o VIP no jogo.');
    return { ok: false, motivo: 'sem uuid vinculado' };
  }

  try {
    const resp = await fetch(MC_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: MC_WEBHOOK_TOKEN,
        uuid: uuidJogador,
        pacote: pacote,     // precisa bater com uma chave de "webhook.vip_pacotes" no config.yml (ex: VIP_MENSAL)
        valor: Number(valor)
      })
    });
    if (!resp.ok) {
      const corpo = await resp.text().catch(function() { return ''; });
      console.error('LegendQuest: webhook recusou a compra:', resp.status, corpo);
      return { ok: false, motivo: 'status ' + resp.status };
    }
    return { ok: true };
  } catch (e) {
    console.error('LegendQuest: erro ao chamar o webhook /compra:', e);
    return { ok: false, motivo: e.message };
  }
}

// Percorre os itens de um pedido confirmado; para cada um que tiver um
// "pacote" do LegendQuest configurado, avisa o plugin no servidor de Minecraft.
async function processarLegendQuestDoPedido(pedido, produtos, vinculos) {
  if (!pedido.itens || !pedido.itens.length) return;

  const vinculo = vinculos[pedido.discord_id];
  const uuid = vinculo ? vinculo.uuid : null;

  for (const item of pedido.itens) {
    if (!item.id) continue;
    const produto = produtos.find(function(p) { return p.id === item.id; });
    if (!produto || !produto.legendquestPacote) continue;

    const valorItem = Number(item.preco) * Number(item.quantidade || 1);
    await notificarCompraLegendQuest(uuid, produto.legendquestPacote, valorItem);
  }
}

module.exports = { notificarCompraLegendQuest, processarLegendQuestDoPedido };
