import { it, expect, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  sendMessageSlack: vi.fn(async () => ({ messageId: "m1", channelId: "c1" })),
}));

vi.mock("../../slack/send.js", () => ({
  sendMessageSlack: mocks.sendMessageSlack,
}));

const { routeReply } = await import("../../auto-reply/reply/route-reply.js");

it("when payload.text is only whitespace and mediaUrls present, first media caption is empty string", async () => {
  mocks.sendMessageSlack.mockClear();

  await routeReply({
    payload: { text: "   ", mediaUrls: ["https://example.test/img.png"] },
    channel: "slack",
    to: "channel:C123",
    cfg: {} as never,
  });

  // Single assertion: the caption (text) passed to the provider for the first media must be the empty string, not whitespace.
  expect(mocks.sendMessageSlack.mock.calls[0][1]).toBe("");
});
