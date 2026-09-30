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


  __testAugmentVitest_67fef0fae449.it("rejects_ipv4_loopback_127_round_010_pass_03", async () => {
    // IPv4 loopback 127.x.x.x should be rejected as a private address.
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn();
    const provider = new LocalFetchURLProvider({ fetchImpl });

    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('http://127.0.0.1/')).rejects.toThrow(/Refusing to fetch private address/);
    __testAugmentVitest_67fef0fae449.expect(fetchImpl).not.toHaveBeenCalled();
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
