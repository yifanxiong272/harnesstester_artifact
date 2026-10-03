import { test, expect, vi } from 'vitest';
import { deliverOutboundPayloads } from '../../infra/outbound/deliver';

test('whatsapp: HTML-only text with no media is treated as empty and not sent', async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: 'w-mock', toJid: 'jid' });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } } as const;

  const results = await deliverOutboundPayloads({
    cfg,
    channel: 'whatsapp',
    to: '+1555',
    payloads: [{ text: '<br>\n <b></b> ' }],
    deps: { sendWhatsApp },
  });

  const observation = { calls: sendWhatsApp.mock.calls.length, resultsLength: results.length };
  expect(observation).toEqual({ calls: 0, resultsLength: 0 });
});
