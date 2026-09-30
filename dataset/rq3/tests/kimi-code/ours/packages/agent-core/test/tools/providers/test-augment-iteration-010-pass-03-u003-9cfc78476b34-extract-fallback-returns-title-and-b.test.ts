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


  __testAugmentVitest_67fef0fae449.it("extract_fallback_returns_title_and_body_round_010_pass_03", async () => {
    // Mock Readability to ensure the primary extractor yields no article so the
    // fallback path is followed. Mock linkedom's parseHTML to return a
    // document with a title and an <article> container with textContent.
    __testAugmentVitest_67fef0fae449.vi.doMock('@mozilla/readability', () => ({
      Readability: class {
        constructor(_doc: any, _opts?: any) {
          /* no-op */
        }
        parse() {
          // Force primary extractor to indicate 'no article' so the fallback runs.
          return null;
        }
      },
    }));

    __testAugmentVitest_67fef0fae449.vi.doMock('linkedom', () => ({
      parseHTML: (html: string) => {
        return {
          document: {
            // title selector should return an element with textContent
            querySelector: (selector: string) => {
              if (selector === 'title') return { textContent: 'My Title' };
              if (selector === 'article') return { textContent: 'Fallback extracted body' };
              if (selector === 'main') return null;
              if (selector === 'body') return { textContent: '' };
              return null;
            },
          },
        };
      },
    }));

    // Load the target module after mocking so our mocks are used.
    const mod = await __testAugmentLoadTarget_5b6333ac9fce();
    const { LocalFetchURLProvider } = mod;

    const html = '<html><head><title>unused</title></head><body><article>ignored</article></body></html>';
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (k: string) => (k === 'content-type' ? 'text/html; charset=utf-8' : null) },
      body: undefined,
      text: async () => html,
    });

    const provider = new LocalFetchURLProvider({ fetchImpl });

    const result = await provider.fetch('https://example.com/fallback-title');

    __testAugmentVitest_67fef0fae449.expect(result.kind).toBe('extracted');
    // The provider formats fallback output as '# {title}\n\n{fallbackText}'.
    __testAugmentVitest_67fef0fae449.expect(result.content).toBe('# My Title\n\nFallback extracted body');
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
