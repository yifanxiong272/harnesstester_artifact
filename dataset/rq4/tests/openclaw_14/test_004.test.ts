import { it, expect, vi } from 'vitest';
import { deliverOutboundPayloads } from '../../infra/outbound/deliver';

it('whatsapp: block-level tag with attributes becomes paragraph with surrounding newlines and is sent', async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: 'w1', toJid: 'jid' });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: 'whatsapp',
    to: '+1555',
    payloads: [{ text: '<p class="x">para</p>' }],
    deps: { sendWhatsApp },
  });

  const sentTextMatches = sendWhatsApp.mock.calls.length > 0 && sendWhatsApp.mock.calls[0][1] === '\npara\n';
  const gotResult = results.some(r => r.messageId === 'w1');
  expect(sentTextMatches && gotResult).toBe(true);
});
