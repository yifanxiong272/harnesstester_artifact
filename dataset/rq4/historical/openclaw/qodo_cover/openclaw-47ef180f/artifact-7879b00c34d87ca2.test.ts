import { describe, expect, it, vi } from "vitest";
import type { ReplyPayload } from "../../../auto-reply/types.js";
import { telegramOutbound } from "./telegram.js";
import { createDirectTextMediaOutbound } from "./direct-text-media.js";
import { createScopedChannelMediaMaxBytesResolver } from "./direct-text-media.js";

describe("telegramOutbound", () => {
  it("passes parsed reply/thread ids for sendText", async () => {
    const sendTelegram = vi.fn().mockResolvedValue({ messageId: "tg-text-1", chatId: "123" });
    const sendText = telegramOutbound.sendText;
    expect(sendText).toBeDefined();

    const result = await sendText!({
      cfg: {},
      to: "123",
      text: "<b>hello</b>",
      accountId: "work",
      replyToId: "44",
      threadId: "55",
      deps: { sendTelegram },
    });

    expect(sendTelegram).toHaveBeenCalledWith(
      "123",
      "<b>hello</b>",
      expect.objectContaining({
        textMode: "html",
        verbose: false,
        accountId: "work",
        replyToMessageId: 44,
        messageThreadId: 55,
      }),
    );
    expect(result).toEqual({ channel: "telegram", messageId: "tg-text-1", chatId: "123" });
  });

  it("parses scoped DM thread ids for sendText", async () => {
    const sendTelegram = vi.fn().mockResolvedValue({ messageId: "tg-text-2", chatId: "12345" });
    const sendText = telegramOutbound.sendText;
    expect(sendText).toBeDefined();

    await sendText!({
      cfg: {},
      to: "12345",
      text: "<b>hello</b>",
      accountId: "work",
      threadId: "12345:99",
      deps: { sendTelegram },
    });

    expect(sendTelegram).toHaveBeenCalledWith(
      "12345",
      "<b>hello</b>",
      expect.objectContaining({
        textMode: "html",
        verbose: false,
        accountId: "work",
        messageThreadId: 99,
      }),
    );
  });

  it("passes media options for sendMedia", async () => {
    const sendTelegram = vi.fn().mockResolvedValue({ messageId: "tg-media-1", chatId: "123" });
    const sendMedia = telegramOutbound.sendMedia;
    expect(sendMedia).toBeDefined();

    const result = await sendMedia!({
      cfg: {},
      to: "123",
      text: "caption",
      mediaUrl: "https://example.com/a.jpg",
      mediaLocalRoots: ["/tmp/media"],
      accountId: "default",
      deps: { sendTelegram },
    });

    expect(sendTelegram).toHaveBeenCalledWith(
      "123",
      "caption",
      expect.objectContaining({
        textMode: "html",
        verbose: false,
        mediaUrl: "https://example.com/a.jpg",
        mediaLocalRoots: ["/tmp/media"],
      }),
    );
    expect(result).toEqual({ channel: "telegram", messageId: "tg-media-1", chatId: "123" });
  });

  it("sends payload media list and applies buttons only to first message", async () => {
    const sendTelegram = vi
      .fn()
      .mockResolvedValueOnce({ messageId: "tg-1", chatId: "123" })
      .mockResolvedValueOnce({ messageId: "tg-2", chatId: "123" });
    const sendPayload = telegramOutbound.sendPayload;
    expect(sendPayload).toBeDefined();

    const payload: ReplyPayload = {
      text: "caption",
      mediaUrls: ["https://example.com/1.jpg", "https://example.com/2.jpg"],
      channelData: {
        telegram: {
          quoteText: "quoted",
          buttons: [[{ text: "Approve", callback_data: "ok" }]],
        },
      },
    };

    const result = await sendPayload!({
      cfg: {},
      to: "123",
      text: "",
      payload,
      mediaLocalRoots: ["/tmp/media"],
      accountId: "default",
      deps: { sendTelegram },
    });

    expect(sendTelegram).toHaveBeenCalledTimes(2);
    expect(sendTelegram).toHaveBeenNthCalledWith(
      1,
      "123",
      "caption",
      expect.objectContaining({
        mediaUrl: "https://example.com/1.jpg",
        quoteText: "quoted",
        buttons: [[{ text: "Approve", callback_data: "ok" }]],
      }),
    );
    expect(sendTelegram).toHaveBeenNthCalledWith(
      2,
      "123",
      "",
      expect.objectContaining({
        mediaUrl: "https://example.com/2.jpg",
        quoteText: "quoted",
      }),
    );
    const secondCallOpts = sendTelegram.mock.calls[1]?.[2] as Record<string, unknown>;
    expect(secondCallOpts?.buttons).toBeUndefined();
    expect(result).toEqual({ channel: "telegram", messageId: "tg-2", chatId: "123" });
  });

  it("sendPayload without mediaUrls delegates to sendText and returns its result", async () => {
    const sendTextMock = vi.fn().mockResolvedValue({ messageId: "txt-1" });
    const outbound = createDirectTextMediaOutbound({
      channel: "imessage",
      resolveSender: (_deps?: unknown) => sendTextMock,
      resolveMaxBytes: () => undefined,
      buildTextOptions: (opts: any) => ({ type: "text", ...opts }),
      buildMediaOptions: (opts: any) => ({ type: "media", ...opts }),
    });
  
    const payload = {
      text: "plain text",
      channelData: {},
    } as any;
  
    const result = await outbound.sendPayload!({
      cfg: {},
      to: "TO-TXT",
      text: "ignored",
      payload,
      mediaLocalRoots: [],
      accountId: "acct",
      deps: {},
    } as any);
  
    expect(sendTextMock).toHaveBeenCalledTimes(1);
    // sendText should be called with the payload text (or ctx.payload.text ?? "")
    expect(sendTextMock).toHaveBeenCalledWith(
      "TO-TXT",
      "plain text",
      expect.objectContaining({
        type: "text",
        mediaUrl: undefined,
      }),
    );
    expect(result).toEqual({ channel: "imessage", messageId: "txt-1" });
  });


  it("sendPayload with multiple mediaUrls calls sendMedia multiple times and returns last result", async () => {
    // mock send fn to return different results for each call
    const sendMediaMock = vi
      .fn()
      .mockResolvedValueOnce({ messageId: "m-1" })
      .mockResolvedValueOnce({ messageId: "m-2" });
  
    const outbound = createDirectTextMediaOutbound({
      channel: "imessage",
      // return the actual sender function
      resolveSender: (_deps?: unknown) => sendMediaMock,
      resolveMaxBytes: () => undefined,
      buildTextOptions: (opts: any) => ({ type: "text", ...opts }),
      buildMediaOptions: (opts: any) => ({ type: "media", ...opts }),
    });
  
    const payload = {
      text: "caption",
      mediaUrls: ["https://ex/1.jpg", "https://ex/2.jpg"],
      channelData: {},
    } as any;
  
    const result = await outbound.sendPayload!({
      cfg: {},
      to: "123",
      text: "",
      payload,
      mediaLocalRoots: ["/tmp"],
      accountId: "acct",
      deps: {},
    } as any);
  
    // two media sends
    expect(sendMediaMock).toHaveBeenCalledTimes(2);
    // first call should include the caption and the first media url
    expect(sendMediaMock).toHaveBeenNthCalledWith(
      1,
      "123",
      "caption",
      expect.objectContaining({
        type: "media",
        mediaUrl: "https://ex/1.jpg",
      }),
    );
    // second call should have empty text and second media url
    expect(sendMediaMock).toHaveBeenNthCalledWith(
      2,
      "123",
      "",
      expect.objectContaining({
        type: "media",
        mediaUrl: "https://ex/2.jpg",
      }),
    );
    // result should be the last send result merged with channel
    expect(result).toEqual({ channel: "imessage", messageId: "m-2" });
  });


  it("sendText uses resolveSender and resolves maxBytes and returns channel in result", async () => {
    const sendMock = vi.fn().mockResolvedValue({ messageId: "sent-1", extra: "ok" });
    const outbound = createDirectTextMediaOutbound({
      channel: "signal",
      // resolveSender should return the actual send function
      resolveSender: (_deps?: unknown) => sendMock,
      resolveMaxBytes: (_params: any) => 123,
      buildTextOptions: (opts: any) => ({ builtFor: "text", ...opts }),
      buildMediaOptions: (opts: any) => ({ builtFor: "media", ...opts }),
    });
  
    const result = await outbound.sendText!({
      cfg: {},
      to: "TO-1",
      text: "Hello",
      accountId: "acct-1",
      deps: { some: "dep" },
      replyToId: "reply-99",
    } as any);
  
    expect(sendMock).toHaveBeenCalledTimes(1);
    const callArgs = sendMock.mock.calls[0];
    expect(callArgs[0]).toBe("TO-1"); // to
    expect(callArgs[1]).toBe("Hello"); // text
    // options built by buildTextOptions should include maxBytes and forwarded metadata
    expect(callArgs[2]).toEqual(
      expect.objectContaining({
        builtFor: "text",
        accountId: "acct-1",
        replyToId: "reply-99",
        maxBytes: 123,
      }),
    );
    // result should include channel merged
    expect(result).toEqual({ channel: "signal", messageId: "sent-1", extra: "ok" });
  });


  it("resolves scoped channel media max bytes with account override and fallback (bytes)", () => {
    const resolver = createScopedChannelMediaMaxBytesResolver("imessage");
    const cfgWithAccount = {
      channels: {
        imessage: {
          mediaMaxMb: 2,
          accounts: {
            work: { mediaMaxMb: 4 },
          },
        },
      },
    } as any;
    const MB = 1024 * 1024;
    // account-specific override (4 MB -> bytes)
    expect(resolver({ cfg: cfgWithAccount, accountId: "work" })).toBe(4 * MB);
    // fallback to channel-level (2 MB -> bytes)
    expect(resolver({ cfg: cfgWithAccount, accountId: "other" })).toBe(2 * MB);
    // undefined when config missing
    expect(resolver({ cfg: {} as any })).toBeUndefined();
  });

});
