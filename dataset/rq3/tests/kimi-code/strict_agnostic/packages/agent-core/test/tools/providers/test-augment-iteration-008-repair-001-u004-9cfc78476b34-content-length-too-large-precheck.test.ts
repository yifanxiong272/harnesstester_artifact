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


  __testAugmentVitest_67fef0fae449.it("content-length-too-large_precheck_round_008", async () => {
    const maxBytes = 10;
    // Return a response-like object whose content-length header exceeds maxBytes.
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (k: string) => (k === 'content-length' ? String(maxBytes + 1) : null) },
      text: async () => 'this body should not be consumed',
    });

    const provider = new LocalFetchURLProvider({ fetchImpl, maxBytes });

    // The provider should reject early due to the content-length header exceeding maxBytes.
    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/large')).rejects.toThrow('Response body too large');
    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/large')).rejects.toThrow(`exceeds maxBytes (${String(maxBytes)})`);
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
