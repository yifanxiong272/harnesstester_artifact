import { it, expect } from "vitest";
import { extractAssistantText } from "../../agents/pi-embedded-utils";

// Activation: single text block exactly 'Before<thinking/>After'
it("removes a self-closing <thinking/> tag but preserves following text", () => {
  const msg = {
    role: "assistant",
    content: [
      { type: "text", text: "Before<thinking/>After" }
    ],
    // Deterministic fixed timestamp; not used by the target logic but included for shape completeness.
    timestamp: 0,
  } as any;

  const result = extractAssistantText(msg);
  expect(result).toBe("BeforeAfter");
});
