import { test, expect, vi } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

test("whatsapp plain-text conversion preserves paragraph boundaries for block tags with attributes", async () => {
  // Deterministic mock for the channel send function
  const sendWhatsApp = vi.fn().mockResolvedValue({ messageId: "w1", toJid: "jid" });

  const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } };
  const params = {
    cfg,
    channel: "whatsapp" as const,
    to: "+1555",
    payloads: [{ text: '<p class="x">para</p>' }],
    deps: { sendWhatsApp },
  };

  const results = await deliverOutboundPayloads(params);

  // Combine both observations into a single boolean and assert once.
  const sentTextIsPreserved =
    Array.isArray(sendWhatsApp.mock.calls) &&
    sendWhatsApp.mock.calls.length > 0 &&
    sendWhatsApp.mock.calls[0][1] === "\npara\n";
  const returnedResultSeen = results.some((r: any) => r && r.messageId === "w1");
  const ok = sentTextIsPreserved && returnedResultSeen;

  expect(ok).toBe(true);
});
