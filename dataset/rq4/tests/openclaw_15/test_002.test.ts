import { test, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

test("whatsapp: HTML-only payload is not sent to provider", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };
  const payloads = [{ text: "<br>\n <b></b>   " }];

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads,
    deps: { sendWhatsApp },
  });

  const observed = { calls: sendWhatsApp.mock.calls.length, resultsLength: Array.isArray(results) ? results.length : 0 };
  expect(observed).toEqual({ calls: 0, resultsLength: 0 });
});
