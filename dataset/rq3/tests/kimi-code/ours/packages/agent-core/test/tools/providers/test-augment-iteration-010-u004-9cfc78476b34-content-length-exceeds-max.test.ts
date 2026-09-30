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


  __testAugmentVitest_67fef0fae449.it("throws_when_content_length_exceeds_max_bytes_round_010", async () => {
    // Make a provider with a tiny maxBytes so the content-length guard triggers.
    const maxBytes = 10;
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (_: string) => '9999' }, // content-length far exceeds maxBytes
      body: undefined,
      text: async () => 'small body',
    });
    const provider = new LocalFetchURLProvider({ fetchImpl, maxBytes });

    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/large')).rejects.toThrow(/Response body too large/);

    // Ensure fetch was invoked once before the size check threw.
    __testAugmentVitest_67fef0fae449.expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
