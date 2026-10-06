import { it, expect, vi } from 'vitest';
import { deliverOutboundPayloads } from '../../infra/outbound/deliver';

it('drops whatsapp payloads that consist only of HTML tags and whitespace and returns no results', async () => {
  // Deterministic mock that records invocations and would return a predictable resolved value if called.
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: 'm1', toJid: 'jid' });

  // Deterministic config to avoid chunking side effects.
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

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
