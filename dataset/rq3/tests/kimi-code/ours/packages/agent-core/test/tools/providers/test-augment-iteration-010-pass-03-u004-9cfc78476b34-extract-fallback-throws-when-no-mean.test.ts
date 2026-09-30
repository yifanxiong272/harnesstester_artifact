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


  __testAugmentVitest_67fef0fae449.it("extract_fallback_throws_when_no_meaningful_content_round_010_pass_03", async () => {
    // Make the primary extractor either throw or return no useful content and
    // the fallback document contain no title and an empty body/article/main
    // so the provider should throw the meaningful-content error.
    __testAugmentVitest_67fef0fae449.vi.doMock('@mozilla/readability', () => ({
      Readability: class {
        constructor(_doc: any, _opts?: any) {}
        parse() {
          // Return an article-like object with empty textContent to force fallback
          return { textContent: '', title: '' };
        }
      },
    }));

    __testAugmentVitest_67fef0fae449.vi.doMock('linkedom', () => ({
      parseHTML: (html: string) => ({
        document: {
          querySelector: (selector: string) => {
            // title -> null, article/main/body -> elements with empty textContent
            if (selector === 'title') return null;
            if (selector === 'article') return { textContent: '' };
            if (selector === 'main') return { textContent: '' };
            if (selector === 'body') return { textContent: '' };
            return null;
          },
        },
      }),
    }));

    const mod = await __testAugmentLoadTarget_5b6333ac9fce();
    const { LocalFetchURLProvider } = mod;

    const html = '<html><head></head><body><article></article></body></html>';
    const fetchImpl = __testAugmentVitest_67fef0fae449.vi.fn().mockResolvedValue({
      status: 200,
      statusText: 'OK',
      headers: { get: (_: string) => 'text/html; charset=utf-8' },
      body: undefined,
      text: async () => html,
    });

    const provider = new LocalFetchURLProvider({ fetchImpl });

    await __testAugmentVitest_67fef0fae449.expect(provider.fetch('https://example.com/empty')).rejects.toThrow(/Failed to extract meaningful content/);
  });
});

import * as __testAugmentVitest_67fef0fae449 from "vitest";

const __testAugmentLoadTarget_5b6333ac9fce = async () => {
  __testAugmentVitest_67fef0fae449.vi.doUnmock("../../../src/tools/providers/local-fetch-url.js");
  __testAugmentVitest_67fef0fae449.vi.resetModules();
  return import("../../../src/tools/providers/local-fetch-url.js");
};
