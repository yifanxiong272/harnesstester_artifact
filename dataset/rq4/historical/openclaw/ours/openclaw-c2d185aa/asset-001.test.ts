import { it, expect, vi } from "vitest";

// Hoist deterministic mocks so Vitest can replace the module implementations.
const mocks = vi.hoisted(() => ({
  sendMessageSlack: vi.fn(async (to: string, text: string, opts?: any) => {
    // Deterministic returns: first media -> m1, second media -> m2
    const media = opts?.mediaUrl;
    if (media === "b") return { messageId: "m2", channelId: "c-last" };
    return { messageId: "m1", channelId: "c-first" };
  }),
}));

vi.mock("../../slack/send.js", () => ({
  sendMessageSlack: mocks.sendMessageSlack,
}));

// Import only the public entrypoint under test.
const { routeReply } = await import("../../auto-reply/reply/route-reply.js");

it("treats whitespace-only payload.text as empty when captioning multiple Slack media URLs", async () => {
  // Arrange: whitespace-only text and two truthy mediaUrls in order.
  const payload = { text: "   \n\t", mediaUrls: ["a", "b"] };

  // Act: call the public entrypoint.
  const res = await routeReply({
    payload,
    channel: "slack",
    to: "channel:C123",
    cfg: {} as never,
  });

  // Observe: transform captured mock calls into a compact shape for assertion.
  const calls = mocks.sendMessageSlack.mock.calls.map(([toArg, textArg, opts]: any) => ({
    to: toArg,
    text: textArg,
    mediaUrl: opts?.mediaUrl,
  }));

  // Single primary assertion that encodes all oracle checks.
  expect({ calls, res }).toEqual({
    calls: [
      { to: "channel:C123", text: "", mediaUrl: "a" },
      { to: "channel:C123", text: "", mediaUrl: "b" }
    ],
    res: { ok: true, messageId: "m2" }
  });
});
