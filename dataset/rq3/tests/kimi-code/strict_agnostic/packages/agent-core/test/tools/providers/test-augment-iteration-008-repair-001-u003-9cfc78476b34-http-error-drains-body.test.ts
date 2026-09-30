/**
 * Covers: LocalFetchURLProvider content-kind reporting.
 *
 * Verifies the provider tells callers whether the returned content is a
 * verbatim passthrough of the response body or the main text extracted
 * from an HTML page.
 */

import { describe, expect, it, vi } from 'vitest';

import { LocalFetchURLProvider } from '../../../src/tools/providers/local-fetch-url';

function htmlResponse(body: string, contentType: string): Response {
  return new Response(body, {
    status: 200,
    headers: { 'content-type': contentType },
  });
}

describe('LocalFetchURLProvider content kind', () => {


  __testAugmentVitest_67fef0fae449.it("http-error-drains-body_round_008", async () => {
    // Build a response-like object that includes a body.cancel method to be drained.
    const cancel = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue(undefined);
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 404,
      statusText: 'Not Found',
      headers: { get: (_: string) => null },
      body: { cancel },
      text: async () => 'should not be used',
    });

    const provider = new LocalFetchURLProvider({ fetchImpl });

    // Should throw an HTTP error and the implementation should have attempted to drain the body.
    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/missing')).rejects.toThrow('HTTP 404 Not Found');
    __testAugmentVitest_67fef0fae449.expect(cancel).toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
