import { describe, expect, it } from "vitest";
import { zalouserPlugin } from "./channel.js";
import { vi } from "vitest";

describe("zalouser outbound chunker", () => {
  it("chunks without empty strings and respects limit", () => {
    const chunker = zalouserPlugin.outbound?.chunker;
    expect(chunker).toBeTypeOf("function");
    if (!chunker) {
      return;
    }

    const limit = 10;
    const chunks = chunker("hello world\nthis is a test", limit);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((c) => c.length > 0)).toBe(true);
    expect(chunks.every((c) => c.length <= limit)).toBe(true);
  });

  it("outbound.sendPayload delegates to sendText when no media present", async () => {
    const sendText = vi.fn(async (ctx) => ({ ok: true, messageId: "text:" + (ctx.text ?? "") }));
    const outbound = (zalouserPlugin.outbound as any)!;
    const origSendText = outbound.sendText;
    outbound.sendText = sendText;
  
    try {
      const ctx = {
        payload: { text: "plain text" },
        to: "999",
        accountId: undefined,
        cfg: {},
      } as any;
  
      const result = await zalouserPlugin.outbound!.sendPayload!(ctx);
      expect(result).toBeDefined();
      expect(result.messageId).toBe("text:plain text");
      expect(sendText).toHaveBeenCalledTimes(1);
      // sendText should receive the full context (sanity check)
      expect(sendText.mock.calls[0][0].to).toBe("999");
    } finally {
      outbound.sendText = origSendText;
    }
  });


  it("outbound.sendPayload sends multiple media urls and returns last result", async () => {
    // Prepare spies for sendMedia/sendText and temporarily replace them on the plugin object
    const sendMedia = vi.fn(async (ctx) => ({ ok: true, messageId: "msg:" + ctx.mediaUrl }));
    const sendText = vi.fn(async () => ({ ok: true, messageId: "should-not-be-used" }));
  
    const outbound = (zalouserPlugin.outbound as any)!;
    const origSendMedia = outbound.sendMedia;
    const origSendText = outbound.sendText;
    outbound.sendMedia = sendMedia;
    outbound.sendText = sendText;
  
    try {
      const ctx = {
        payload: { mediaUrls: ["u1", "u2"], text: "hello world" },
        to: "999",
        accountId: undefined,
        cfg: {},
      } as any;
  
      const result = await zalouserPlugin.outbound!.sendPayload!(ctx);
      // result should be from the last media send
      expect(result).toBeDefined();
      expect(result.messageId).toBe("msg:u2");
      // sendMedia called twice, sendText not used
      expect(sendMedia).toHaveBeenCalledTimes(2);
      expect(sendText).toHaveBeenCalledTimes(0);
      // first call carries the original text, second call has empty text
      expect(sendMedia.mock.calls[0][0].text).toBe("hello world");
      expect(sendMedia.mock.calls[1][0].text).toBe("");
    } finally {
      // restore
      outbound.sendMedia = origSendMedia;
      outbound.sendText = origSendText;
    }
  });


  it("pairing.normalizeAllowEntry strips known prefixes", () => {
    const normalize = zalouserPlugin.pairing?.normalizeAllowEntry;
    expect(normalize).toBeTypeOf("function");
    if (!normalize) return;
  
    expect(normalize("zalouser:XYZ")).toBe("XYZ");
    expect(normalize("ZLU:abc")).toBe("abc");
    // no prefix remains unchanged
    expect(normalize("12345")).toBe("12345");
  });


  it("normalizes messaging targets and recognizes numeric ids", () => {
    const normalize = zalouserPlugin.messaging?.normalizeTarget;
    const looksLikeId = zalouserPlugin.messaging?.targetResolver?.looksLikeId;
    expect(normalize).toBeTypeOf("function");
    expect(looksLikeId).toBeTypeOf("function");
    if (!normalize || !looksLikeId) return;
  
    // trimming and prefix stripping (case-insensitive)
    expect(normalize("  zalouser:12345  ")).toBe("12345");
    expect(normalize("zlu:ABC")).toBe("ABC");
    // empty / whitespace-only returns undefined
    expect(normalize("   ")).toBeUndefined();
  
    // looksLikeId: must be at least 3 digits
    expect(looksLikeId("")).toBe(false);
    expect(looksLikeId("12")).toBe(false);
    expect(looksLikeId("123")).toBe(true);
    // leading zeros still count as digits
    expect(looksLikeId("001")).toBe(true);
  });

});
