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


  __testAugmentVitest_67fef0fae449.it("allows_private_when_opt_in_round_010_pass_02", async () => {
    // When allowPrivateAddresses is enabled, previously-private hostnames should be allowed
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (k: string) => (k === 'content-type' ? 'text/plain; charset=utf-8' : null) },
      body: undefined,
      text: async () => 'ok',
    });
    const provider = new LocalFetchURLProvider({ fetchImpl, allowPrivateAddresses: true });

    const result = await provider.fetch('http://127.0.0.1/resource');

    __testAugmentVitest_67fef0fae449.expect(result).toEqual({ content: 'ok', kind: 'passthrough' });
    __testAugmentVitest_67fef0fae449.expect(fetchImpl).toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
