import { it, expect } from "vitest";
import { formatRawAssistantErrorForUi } from "../../shared/assistant-error-format";

it("returns a concise service-unavailable message for a leading HTTP status with an HTML error page", () => {
  const raw = "HTTP 502 Bad Gateway\n\n<!doctype html><html><head><title>502 Bad Gateway</title></head><body><h1>502</h1><p>Cloudflare error</p></body></html>";
  expect(formatRawAssistantErrorForUi(raw)).toBe("The AI service is temporarily unavailable (HTTP 502). Please try again in a moment.");
});
