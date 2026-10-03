import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("does not send whatsapp messages that become empty after HTML sanitization", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "m1", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };
  const payloads = [{ text: "<br>\n \t <b></b>" }];

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads,
    deps: { sendWhatsApp },
  });

  const observation = { calls: sendWhatsApp.mock.calls.length, resultsLength: results.length };
  expect(observation).toEqual({ calls: 0, resultsLength: 0 });
});
