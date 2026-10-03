import { it, expect } from "vitest";
import { extractAssistantText } from "../../agents/pi-embedded-utils";

it("removes a self-closing <thinking/> tag but preserves following text", () => {
  const msg = {
    role: "assistant",
    content: [
      { type: "text", text: "Before<thinking/>After" }
    ],
    timestamp: 0,
  } as const;

  const result = extractAssistantText(msg as any);
  expect(result).toBe("BeforeAfter");
});
