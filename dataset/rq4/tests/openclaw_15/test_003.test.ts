import { it, expect } from "vitest";
import { deliverOutboundPayloads } from "../../infra/outbound/deliver";

// Deterministic config: ensure stable chunking bounds (not relevant here but keeps behavior stable)
const cfg = { channels: { whatsapp: { textChunkLimit: 4000 } } } as const;

// Record invocations in a simple synchronous array. The function returns a predictable resolved value
// if called. This mock is deterministic and has no external effects.
const sendWhatsAppCalls: Array<any> = [];
async function sendWhatsApp(to: string, message: string, opts?: any) {
  sendWhatsAppCalls.push({ to, message, opts });
  return { messageId: "mocked-msg", toJid: "jid" };
}

it("does not send WhatsApp payloads that contain only HTML tags and whitespace (no media)", async () => {
  const results = await deliverOutboundPayloads({
    cfg,
    channel: "whatsapp",
    to: "+1555",
    payloads: [{ text: "<br>\n <b></b>   " }],
    deps: { sendWhatsApp },
  });

  // Single expect as required by the harness: assert both no provider calls and no results returned.
  expect({ calls: sendWhatsAppCalls.length, resultsLength: results.length }).toEqual({ calls: 0, resultsLength: 0 });
});
