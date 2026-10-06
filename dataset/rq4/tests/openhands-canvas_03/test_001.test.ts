import { test, expect, vi } from "vitest";

// Mock the project path alias that the target module's dependency tree imports
// so Vite does not fail to resolve '#/i18n/declaration' at bundle/transform
// time. The mock provides the minimal exported symbol used by the real module.
vi.mock("#/i18n/declaration", () => ({
  // The real module exports a type/identifier I18nKey; tests only need a
  // placeholder object so the module graph can be loaded.
  I18nKey: {},
}));

// Defer loading the target module until runtime (after the mock is installed)
// by using a dynamic import inside the test. This ensures the vi.mock above
// runs before the module is evaluated.
test("parseRuntimeServicesInfo rejects services when services is an Array (string input)", async () => {
  const { parseRuntimeServicesInfo } = await import("../../../src/api/agent-server-adapter");

  const jsonInput = '{"services": []}';
  const result = parseRuntimeServicesInfo(jsonInput);
  expect(result).toBeNull();
});
