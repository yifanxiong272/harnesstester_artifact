import { it, expect, vi } from 'vitest';

// IMPORTANT: mocks must be registered before importing the module under test.
// messenger.ts imports several helpers using relative specifiers; mock the
// exact resolved specifiers used by messenger.ts so the test exercises the
// real public sendMSTeamsMessages entrypoint while avoiding real I/O.

// Mock the plugin SDK loadWebMedia (messenger imports loadWebMedia from here)
vi.mock('openclaw/plugin-sdk', () => {
  return {
    // provide a deterministic loadWebMedia to avoid hitting real filesystem
    loadWebMedia: async (_url: string, _max?: number) => ({
      buffer: Buffer.from('ok'),
      contentType: 'application/pdf',
      fileName: 'doc.pdf',
    }),
    // minimal stubs for other exports that may be referenced at runtime
    isSilentReplyText: (_: string) => false,
    SILENT_REPLY_TOKEN: 'SILENT',
  } as unknown;
});

// Mock the messenger's media helpers (exact relative path used by messenger.ts)
vi.mock('../../../extensions/msteams/src/media-helpers.js', () => {
  return {
    isLocalPath: (_: string) => true,
    getMimeType: async (_: string) => 'application/pdf',
    extractFilename: async (_: string) => 'doc.pdf',
    extractMessageId: (_: string) => undefined,
  } as unknown;
});

// Mock graph-upload (OneDrive fallback)
vi.mock('../../../extensions/msteams/src/graph-upload.js', () => {
  return {
    uploadAndShareOneDrive: async () => ({ name: 'doc.pdf', shareUrl: 'https://onedrive.example/s/abcd' }),
    // provide other exports if imported elsewhere; not used in this test
    uploadAndShareSharePoint: async () => ({ itemId: 'x' }),
    getDriveItemProperties: async () => ({}),
  } as unknown;
});

// Mock mentions parser to deterministically convert the Teams-style token
vi.mock('../../../extensions/msteams/src/mentions.js', () => {
  return {
    parseMentions: (text: string) => {
      const formatted = text.replace('@[Al](28:abc)', '<at>Al</at>');
      const entities = formatted.includes('<at>') ? [{ type: 'mention', text: '<at>Al</at>' }] : [];
      return { text: formatted, entities };
    },
  } as unknown;
});

// Mock file-consent helpers to avoid triggering consent flow
vi.mock('../../../extensions/msteams/src/file-consent-helpers.js', () => {
  return {
    requiresFileConsent: (_: any) => false,
    prepareFileConsentActivity: (_: any) => ({ activity: { type: 'message' } }),
  } as unknown;
});

it('preserves parseMentions formatted text when appending OneDrive file link (OneDrive fallback)', async () => {
  // Import after mocks to ensure messenger loads with our stubs
  const { sendMSTeamsMessages } = await import('../../../extensions/msteams/src/messenger');

  let capturedActivity: any = undefined;

  const adapter = {
    // match the MSTeamsAdapter continueConversation signature used by messenger
    continueConversation: async (_appId: string, _reference: unknown, logic: (ctx: any) => Promise<void>) => {
      await logic({
        sendActivity: async (activity: unknown) => {
          capturedActivity = activity;
          return { id: 'id:ok' };
        },
      });
    },
  };

  const conversationRef = {
    activityId: 'activity123',
    user: { id: 'user123', name: 'User' },
    agent: { id: 'bot123', name: 'Bot' },
    conversation: { id: '19:abc@thread.tacv2', conversationType: 'groupchat' },
    channelId: 'msteams',
    serviceUrl: 'https://service.example.com',
  };

  const tokenProvider = { getToken: async () => ({ token: 'tok' }) } as unknown;

  await sendMSTeamsMessages({
    replyStyle: 'top-level',
    adapter: adapter as any,
    appId: 'app123',
    conversationRef: conversationRef as any,
    messages: [{ text: 'Hello @[Al](28:abc)', mediaUrl: '/local/path/doc.pdf' }],
    tokenProvider: tokenProvider as any,
  });

  expect(capturedActivity?.text).toBe('Hello <at>Al</at>\n\n📎 [doc.pdf](https://onedrive.example/s/abcd)');
});
