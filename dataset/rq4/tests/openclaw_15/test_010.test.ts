import { it, expect, vi } from "vitest";

it("drops whatsapp payloads whose text is only HTML/whitespace and does not call sendWhatsApp", async () => {
  // Deterministic mock that records invocations and, if called, returns a predictable resolved value
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "mock-m", toJid: "jid" });

  const cfg = {
    channels: { whatsapp: { textChunkLimit: 4000 } },
  } as unknown;

  // Import the public entrypoint dynamically so any necessary test-time mocks may be applied before import
  const mod = await import("../../infra/outbound/deliver");
  const { deliverOutboundPayloads } = mod as {
    deliverOutboundPayloads: (params: any) => Promise<any[]>;
  };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<br>\n <b></b> " }],
    deps: { sendWhatsApp },
  });

  // Single assertion: no sendWhatsApp calls and no results returned
  expect({ calls: sendWhatsApp.mock.calls.length, resultsLength: results.length }).toEqual({ calls: 0, resultsLength: 0 });
});
