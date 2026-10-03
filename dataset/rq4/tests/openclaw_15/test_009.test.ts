import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("treats HTML-only WhatsApp payload as empty and does not call sendWhatsApp", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<br>\n <b></b> " }],
    deps: { sendWhatsApp },
  });

  const observation = { calls: sendWhatsApp.mock.calls.length, resultsLength: results.length };
  expect(observation).toEqual({ calls: 0, resultsLength: 0 });
});
