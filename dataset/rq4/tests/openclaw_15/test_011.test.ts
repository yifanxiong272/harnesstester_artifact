import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("does not send whatsapp messages for html-only payloads without media", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock-id", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<br>\n  <b></b>   " }],
    deps: { sendWhatsApp },
  });

  const observed = { calls: sendWhatsApp.mock.calls.length, resultsLength: results.length };
  expect(observed).toEqual({ calls: 0, resultsLength: 0 });
});
