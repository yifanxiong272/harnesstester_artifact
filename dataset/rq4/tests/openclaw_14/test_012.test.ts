import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("whatsapp: preserves paragraph boundaries for block tags with attributes when converting to plain text", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "w1", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: '<p class="x">para</p>' }],
    deps: { sendWhatsApp },
  });

  expect(sendWhatsApp.mock.calls[0][1] === "\npara\n" && results.some(r => r.messageId === "w1")).toBe(true);
});
