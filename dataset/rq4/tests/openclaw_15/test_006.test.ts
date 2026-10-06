import { test, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

// Single test that exercises the public entrypoint with a payload
// whose text contains only HTML tags and whitespace.
test("deliverOutboundPayloads: drop HTML-only WhatsApp payloads (no media)", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock", toJid: "jid" });

  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } } as any;

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<br>\n <b></b> " }],
    deps: { sendWhatsApp },
  });

  // Single assertion oracle: no provider calls and no results for HTML-only payload
  expect({ calls: sendWhatsApp.mock.calls.length, resultsLength: results.length }).toEqual({
    calls: 0,
    resultsLength: 0,
  });
});
