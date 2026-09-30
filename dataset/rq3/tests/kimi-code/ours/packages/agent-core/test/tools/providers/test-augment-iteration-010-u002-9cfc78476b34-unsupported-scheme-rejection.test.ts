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


  __testAugmentVitest_67fef0fae449.it("throws_on_unsupported_scheme_round_010", async () => {
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn();
    const provider = new LocalFetchURLProvider({ fetchImpl });

    // Unsupported scheme (ftp) should be rejected specifically mentioning the scheme.
    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('ftp://example.com/resource')).rejects.toThrow(/Unsupported URL scheme "ftp:"/);

    // fetchImpl must not be called when scheme is rejected.
    __testAugmentVitest_67fef0fae449.expect(fetchImpl).not.toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
