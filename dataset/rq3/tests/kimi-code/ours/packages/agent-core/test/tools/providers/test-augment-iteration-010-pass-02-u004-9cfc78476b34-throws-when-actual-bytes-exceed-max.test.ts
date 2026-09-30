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


  __testAugmentVitest_67fef0fae449.it("throws_when_actual_bytes_exceed_max_round_010_pass_02", async () => {
    // When content-length is absent, provider measures the buffered body and should reject if it exceeds maxBytes.
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (_: string) => null }, // no content-length header
      body: undefined,
      text: async () => 'abcdef', // 6 bytes
    });
    const provider = new LocalFetchURLProvider({ fetchImpl, maxBytes: 5 });

    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/too-big')).rejects.toThrow(/Response body too large/);

    __testAugmentVitest_67fef0fae449.expect(fetchImpl).toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
