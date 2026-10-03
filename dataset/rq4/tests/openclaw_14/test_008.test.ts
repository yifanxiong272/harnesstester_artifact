import { it, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

it("preserves paragraph boundaries for block-level tags with attributes when sending to whatsapp", async () => {
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "w1", toJid: "jid" });
  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };
  const payloads = [{ text: "<p class=\"x\">para</p>" }];

  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads,
    deps: { sendWhatsApp },
  });

  // Inspect the first call to the mocked sendWhatsApp. The message text is the second positional arg.
  const firstCall = sendWhatsApp.mock.calls[0];
  const sentText = firstCall && firstCall[1];

  const ok = sentText === "\npara\n" && Array.isArray(results) && results.some((r) => r && r.messageId === "w1");
  expect(ok).toBe(true);
});
