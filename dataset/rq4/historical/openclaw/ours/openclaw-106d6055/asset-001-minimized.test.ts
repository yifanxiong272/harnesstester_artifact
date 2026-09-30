import { it, expect, vi } from "vitest";

vi.mock("openclaw/plugin-sdk", async () => {
  const actual = await vi.importActual<typeof import("openclaw/plugin-sdk")>("openclaw/plugin-sdk").catch(() => ({} as any));
  return {
    ...(actual || {}),
    loadWebMedia: async (_p: string, _max: number) => ({ buffer: Buffer.from("dummy"), contentType: "application/pdf", fileName: "doc.pdf" }),
  };
});

vi.mock("../../../extensions/msteams/src/media-helpers.js", async () => {
  const actual = await vi.importActual<typeof import("../../../extensions/msteams/src/media-helpers.js")>("../../../extensions/msteams/src/media-helpers.js").catch(() => ({} as any));
  return {
    ...(actual || {}),
    isLocalPath: (_p: string) => true,
    getMimeType: async (_p: string) => "application/pdf",
    extractFilename: async (_p: string) => "doc.pdf",
  };
});

vi.mock("../../../extensions/msteams/src/file-consent-helpers.js", async () => {
  const actual = await vi.importActual<typeof import("../../../extensions/msteams/src/file-consent-helpers.js")>("../../../extensions/msteams/src/file-consent-helpers.js").catch(() => ({} as any));
  return {
    ...(actual || {}),
    requiresFileConsent: (_opts: any) => false,
    prepareFileConsentActivity: (_opts: any) => ({ activity: { type: "message", text: "consent" } }),
  };
});

vi.mock("../../../extensions/msteams/src/graph-upload.js", async () => {
  const actual = await vi.importActual<typeof import("../../../extensions/msteams/src/graph-upload.js")>("../../../extensions/msteams/src/graph-upload.js").catch(() => ({} as any));
  return {
    ...(actual || {}),
    uploadAndShareOneDrive: async (_opts: any) => ({ name: "doc.pdf", shareUrl: "https://share" }),
  };
});

import { setMSTeamsRuntime } from "../../../extensions/msteams/src/runtime";
setMSTeamsRuntime({
  channel: {
    text: {
      chunkMarkdownText: (t: string, _l: number) => (t ? [t] : []),
      chunkMarkdownTextWithMode: (t: string, _l: number) => (t ? [t] : []),
      resolveMarkdownTableMode: () => "code",
      convertMarkdownTables: (text: string) => text,
    },
  },
} as any);

import { sendMSTeamsMessages } from "../../../extensions/msteams/src/messenger";

it("preserves formatted mention text when appending OneDrive file link (OneDrive fallback)", async () => {
  const captured: { activity?: Record<string, any> } = {};

  const adapter = {
    continueConversation: async (_appId: string, _reference: unknown, logic: (c: any) => Promise<void>) => {
      await logic({
        sendActivity: async (activity: unknown) => {
          captured.activity = activity as Record<string, any>;
          return { id: `id:${(activity as any)?.text ?? ""}` };
        },
      });
    },
  } as any;

  const baseRef = {
    activityId: "activity123",
    user: { id: "user123", name: "User" },
    agent: { id: "bot123", name: "Bot" },
    conversation: { id: "19:abc@thread.tacv2;messageid=deadbeef" },
    channelId: "msteams",
    serviceUrl: "https://service.example.com",
  } as any;

  const messages = [{ text: "Hello @[Al](28:abc)", mediaUrl: "/local/path/doc.pdf" }];

  const tokenProvider = { getToken: async () => "tok" } as any;

  await sendMSTeamsMessages({
    replyStyle: "top-level",
    adapter: adapter as any,
    appId: "app123",
    conversationRef: baseRef,
    messages,
    tokenProvider,
  });

  expect(captured.activity?.text).toEqual("Hello <at>Al</at>\n\n📎 [doc.pdf](https://share)");
});
