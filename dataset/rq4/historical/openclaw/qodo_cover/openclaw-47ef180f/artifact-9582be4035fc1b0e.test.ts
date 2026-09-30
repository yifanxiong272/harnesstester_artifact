import type { OpenClawConfig, RuntimeEnv } from "openclaw/plugin-sdk";
import { describe, expect, it } from "vitest";
import { zaloPlugin } from "./channel.js";
import { vi } from "vitest";
import * as sendModule from "./send.js";
import { DEFAULT_ACCOUNT_ID } from "openclaw/plugin-sdk";

describe("zalo directory", () => {
  const runtimeEnv: RuntimeEnv = {
    log: () => {},
    error: () => {},
    exit: (code: number): never => {
      throw new Error(`exit ${code}`);
    },
  };

  it("lists peers from allowFrom", async () => {
    const cfg = {
      channels: {
        zalo: {
          allowFrom: ["zalo:123", "zl:234", "345"],
        },
      },
    } as unknown as OpenClawConfig;

    expect(zaloPlugin.directory).toBeTruthy();
    expect(zaloPlugin.directory?.listPeers).toBeTruthy();
    expect(zaloPlugin.directory?.listGroups).toBeTruthy();

    await expect(
      zaloPlugin.directory!.listPeers!({
        cfg,
        accountId: undefined,
        query: undefined,
        limit: undefined,
        runtime: runtimeEnv,
      }),
    ).resolves.toEqual(
      expect.arrayContaining([
        { kind: "user", id: "123" },
        { kind: "user", id: "234" },
        { kind: "user", id: "345" },
      ]),
    );

    await expect(
      zaloPlugin.directory!.listGroups!({
        cfg,
        accountId: undefined,
        query: undefined,
        limit: undefined,
        runtime: runtimeEnv,
      }),
    ).resolves.toEqual([]);
  });

  it("outbound sendText/sendMedia/sendPayload map sendMessageZalo results and handle media arrays", async () => {
    // spy on the module function to avoid real network calls
    const spy = vi.spyOn(sendModule, "sendMessageZalo").mockImplementation((to: string, text: string, opts: any) => {
      // if mediaUrl present, return messageId based on mediaUrl, otherwise use text
      if (opts && opts.mediaUrl) {
        return Promise.resolve({ ok: true, messageId: `m:${opts.mediaUrl}` });
      }
      return Promise.resolve({ ok: true, messageId: `t:${text}` });
    });
    try {
      // sendText path
      const rText = await zaloPlugin.outbound!.sendText!({
        to: "100",
        text: "hello",
        accountId: undefined,
        cfg: {},
      } as any);
      expect(rText.channel).toEqual("zalo");
      expect(rText.ok).toBe(true);
      expect(rText.messageId).toEqual("t:hello");
      expect(rText.error).toBeUndefined();
      // sendMedia path
      const rMedia = await zaloPlugin.outbound!.sendMedia!({
        to: "100",
        text: "caption",
        mediaUrl: "http://img/1",
        accountId: undefined,
        cfg: {},
      } as any);
      expect(rMedia.channel).toEqual("zalo");
      expect(rMedia.ok).toBe(true);
      expect(rMedia.messageId).toEqual("m:http://img/1");
      // sendPayload with multiple mediaUrls should return last media result
      const ctx = {
        to: "100",
        accountId: undefined,
        cfg: {},
        payload: { text: "ignored", mediaUrls: ["http://img/1", "http://img/2"] },
      } as any;
      const rPayload = await zaloPlugin.outbound!.sendPayload!(ctx);
      expect(rPayload.channel).toEqual("zalo");
      expect(rPayload.ok).toBe(true);
      expect(rPayload.messageId).toEqual("m:http://img/2"); // last mediaUrl result
      // sendPayload with no media should call sendText
      const rPayloadText = await zaloPlugin.outbound!.sendPayload!({
        to: "100",
        accountId: undefined,
        cfg: {},
        payload: { text: "only-text" },
      } as any);
      expect(rPayloadText.messageId).toEqual("t:only-text");
    } finally {
      spy.mockRestore();
    }
  });


  it("setup.validateInput enforces useEnv and token/tokenFile rules", async () => {
    // non-default account cannot use env
    const bad = zaloPlugin.setup.validateInput!({
      accountId: "other-account",
      input: { useEnv: true },
    } as any);
    expect(bad).toMatch(/ZALO_BOT_TOKEN can only be used for the default account/);
    // default account can use env (no error)
    const okDefault = zaloPlugin.setup.validateInput!({
      accountId: DEFAULT_ACCOUNT_ID,
      input: { useEnv: true },
    } as any);
    expect(okDefault).toBeNull();
    // missing token and tokenFile when not useEnv -> error
    const missingToken = zaloPlugin.setup.validateInput!({
      accountId: DEFAULT_ACCOUNT_ID,
      input: { useEnv: false, token: "", tokenFile: "" },
    } as any);
    expect(missingToken).toMatch(/Zalo requires token or --token-file/);
  });


  it("targetResolver.looksLikeId recognizes numeric chat IDs correctly", async () => {
    const looksLike = zaloPlugin.messaging.targetResolver!.looksLikeId;
    expect(looksLike("")).toBe(false);
    expect(looksLike("  ")).toBe(false);
    expect(looksLike("12")).toBe(false); // too short
    expect(looksLike("123")).toBe(true); // minimal acceptable
    expect(looksLike("  00123  ")).toBe(true); // trims whitespace
    expect(looksLike("abc123")).toBe(false); // not purely digits
  });


  it("normalizeTarget strips prefixes and handles empty input", async () => {
    // prefix stripping and trimming
    expect(zaloPlugin.messaging.normalizeTarget?.(" zalo:123 ")).toEqual("123");
    expect(zaloPlugin.messaging.normalizeTarget?.("zl:ABC")).toEqual("ABC");
    // no prefix leaves value intact (but trimmed)
    expect(zaloPlugin.messaging.normalizeTarget?.("  someId  ")).toEqual("someId");
    // blank / empty -> undefined
    expect(zaloPlugin.messaging.normalizeTarget?.("")).toBeUndefined();
    expect(zaloPlugin.messaging.normalizeTarget?.("   ")).toBeUndefined();
  });

});
