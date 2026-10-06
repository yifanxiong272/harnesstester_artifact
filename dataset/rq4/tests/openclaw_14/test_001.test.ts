import { it, expect } from "vitest";
import { sanitizeForPlainText } from "../../infra/outbound/sanitize-text";

it("converts attribute-bearing block tags (<p> with attributes) to surrounding newlines", () => {
  const input = '<p class="x">para</p>';
  const result = sanitizeForPlainText(input);
  expect(result).toBe('\npara\n');
});
