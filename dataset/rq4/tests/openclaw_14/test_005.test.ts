import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("whatsapp plain-text conversion preserves paragraph boundaries for block tags with attributes", async () => {
  // Deterministic mock for the channel send routine
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "w1", toJid: "jid" });

  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: '<p class="x">para</p>' }],
    deps: { sendWhatsApp },
  });

  // Single combined assertion (exactly one expect across the file)
  // Check that the sendWhatsApp first call's message text is exactly '\npara\n'
  // and that the delivery result from the mock was propagated.
  expect((sendWhatsApp.mock.calls[0] && sendWhatsApp.mock.calls[0][1] === "\npara\n") && results.some((r) => r.messageId === "w1")).toBe(true);
});
