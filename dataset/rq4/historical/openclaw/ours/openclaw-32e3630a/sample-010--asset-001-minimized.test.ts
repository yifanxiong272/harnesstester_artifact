import { it, expect } from "vitest";
import { sanitizeToolCallInputs } from "../../agents/session-transcript-repair";

it("preserves a whitespace-padded allowed toolCall and unrelated text block when allowedToolNames includes the trimmed name", () => {
  const messages = [
    {
      role: "assistant",
      content: [
        { type: "toolCall", id: "call_1", name: " read ", arguments: {} },
        { type: "text", text: "preserve me" },
      ],
    },
  ] as unknown as any[];

  const out = sanitizeToolCallInputs(messages, { allowedToolNames: new Set(["read"]) });

  const preserved =
    Array.isArray(out) &&
    out.some(
      (m) =>
        m?.role === "assistant" &&
        Array.isArray(m.content) &&
        m.content.some((b: any) => b?.type === "toolCall" && b?.id === "call_1"),
    ) &&
    out.some(
      (m) =>
        m?.role === "assistant" &&
        Array.isArray(m.content) &&
        m.content.some((b: any) => b?.type === "text" && b?.text === "preserve me"),
    );

  expect(preserved).toBe(true);
});
