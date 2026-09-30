import { test, expect, vi } from "vitest";

// Hoist deterministic mock so the target module picks it up when imported
const mocks = vi.hoisted(() => ({
  sendMessageSlack: vi.fn(async () => ({ messageId: "m1", channelId: "c1" })),
}));

vi.mock("../../slack/send.js", () => ({ sendMessageSlack: mocks.sendMessageSlack }));

// Import the public entrypoint after installing mocks
const { routeReply } = await import("../../auto-reply/reply/route-reply");

test("whitespace-only text is trimmed to empty caption for first media send (slack)", async () => {
  mocks.sendMessageSlack.mockClear();
  const res = await routeReply({
    payload: { text: "   ", mediaUrls: ["https://cdn.example/a.jpg"] },
    channel: "slack",
    to: "channel:C123",
    cfg: {} as never,
  });

  // Composite assertion: ensure routing succeeded and the provider was called with an empty caption
  expect({ ok: res.ok, slackText: mocks.sendMessageSlack.mock.calls[0]?.[1] ?? null }).toEqual({ ok: true, slackText: "" });
});
