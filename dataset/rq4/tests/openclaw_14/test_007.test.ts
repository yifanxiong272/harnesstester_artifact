import { it, vi, expect } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("preserves paragraph boundaries for block-level tags with attributes when sending to whatsapp", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "w1", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: '<p class="x">para</p>' }],
    deps: { sendWhatsApp },
  });

  const sentText = sendWhatsApp.mock.calls[0]?.[1];
  const ok = sentText === "\npara\n" && results.some((r) => r.messageId === "w1");
  expect(ok).toBe(true);
});
