import { it, expect } from "vitest";
import { repairToolCallInputs } from "../../agents/session-transcript-repair";

it("preserves toolCall blocks whose name differs only by surrounding whitespace when allowedToolNames contains the trimmed name", () => {
  const messages = [
    {
      role: "assistant",
      content: [
        { type: "toolCall", id: "call_1", name: " read ", arguments: {} },
        { type: "text", text: "preserve me" },
      ],
    },
  ];

  const report = repairToolCallInputs(messages as any, { allowedToolNames: new Set(["read"]) });

  const preserved =
    report &&
    typeof report.droppedToolCalls === "number" &&
    report.droppedToolCalls === 0 &&
    Array.isArray(report.messages) &&
    report.messages.length === 1 &&
    Array.isArray(report.messages[0].content) &&
    report.messages[0].content.some((b: any) => b?.type === "toolCall" && b?.id === "call_1");

  expect(preserved).toBe(true);
});
