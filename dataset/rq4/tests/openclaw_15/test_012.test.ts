import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("does not send HTML-only WhatsApp payloads with no media", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock-id", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<b></b>" }],
    deps: { sendWhatsApp },
  });

  expect({ calls: sendWhatsApp.mock.calls.length, resultsLength: results.length }).toEqual({
    calls: 0,
    resultsLength: 0,
  });
});
