import { it, expect, vi } from 'vitest';
import { deliverOutboundPayloads } from '../../infra/outbound/deliver';

it('whatsapp html-only payload is not sent and returns no results', async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: 'w1', toJid: 'jid' });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };
  const payloads = [{ text: '<br>\n <b></b>' }];

  const results = await deliverOutboundPayloads({
    cfg,
    channel: 'whatsapp',
    to: '+1555',
    payloads,
    deps: { sendWhatsApp },
  });

  expect({ calls: sendWhatsApp.mock.calls.length, resultsLength: results.length }).toEqual({
    calls: 0,
    resultsLength: 0,
  });
});
