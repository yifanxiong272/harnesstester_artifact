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


  __testAugmentVitest_67fef0fae449.it("cancels_body_and_throws_on_http_error_round_010", async () => {
    // Simulate a 500 response with a body that exposes a cancel() we can observe.
    const cancelMock = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue(undefined);
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 500,
      statusText: 'Internal Server Error',
      headers: { get: (_: string) => null },
      // body?.cancel() is awaited by the provider on error paths
      body: { cancel: cancelMock },
      // text should not be required for the error path, but provide it defensively
      text: async () => 'irrelevant',
    });

    const provider = new LocalFetchURLProvider({ fetchImpl });

    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/broken')).rejects.toThrow(/HTTP 500/);

    // Ensure the provider attempted to cancel/drain the body when status >= 400.
    __testAugmentVitest_67fef0fae449.expect(cancelMock).toHaveBeenCalled();
    __testAugmentVitest_67fef0fae449.expect(fetchImpl).toHaveBeenCalledTimes(1);
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
