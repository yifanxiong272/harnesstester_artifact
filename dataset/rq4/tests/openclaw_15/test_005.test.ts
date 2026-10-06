import { it, expect, vi } from 'vitest';
import { deliverOutboundPayloads } from '../../infra/outbound/deliver';

it('does not send whatsapp payload when text is HTML-only and whitespace', async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: 'w1', toJid: 'jid' });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: 'whatsapp',
    to: '+1555',
    payloads: [{ text: '<br>\n <b></b> ' }],
    deps: { sendWhatsApp },
  });

  expect({ calls: sendWhatsApp.mock.calls.length, resultsLength: results.length }).toEqual({ calls: 0, resultsLength: 0 });
});
