/**
 * Covers: LocalFetchURLProvider content-kind reporting.
 *
 * Verifies the provider tells callers whether the returned content is a
 * verbatim passthrough of the response body or the main text extracted
 * from an HTML page.
 */

import { describe, expect, it, vi } from 'vitest';

import { LocalFetchURLProvider } from '../../../src/tools/providers/local-fetch-url';
import { Readability } from '@mozilla/readability';

function htmlResponse(body: string, contentType: string): Response {
  return new Response(body, {
    status: 200,
    headers: { 'content-type': contentType },
  });
}

describe('LocalFetchURLProvider content kind', () => {
  it('reports text/plain bodies as a verbatim passthrough', async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(htmlResponse('plain body', 'text/plain; charset=utf-8'));
    const provider = new LocalFetchURLProvider({ fetchImpl });

    const result = await provider.fetch('https://example.com/file.txt');

    expect(result).toEqual({ content: 'plain body', kind: 'passthrough' });
  });

  it('reports text/markdown bodies as a verbatim passthrough', async () => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(htmlResponse('# Title\n\nbody', 'text/markdown'));
    const provider = new LocalFetchURLProvider({ fetchImpl });

    const result = await provider.fetch('https://example.com/readme.md');

    expect(result).toEqual({ content: '# Title\n\nbody', kind: 'passthrough' });
  });

  it('reports HTML bodies as extracted main content', async () => {
    const html =
      '<html><head><title>Doc</title></head><body><article>' +
      '<p>The quick brown fox jumps over the lazy dog. '.repeat(20) +
      '</p></article></body></html>';
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(htmlResponse(html, 'text/html; charset=utf-8'));
    const provider = new LocalFetchURLProvider({ fetchImpl });

    const result = await provider.fetch('https://example.com/page');

    expect(result.kind).toBe('extracted');
    expect(result.content).toContain('quick brown fox');
  });

  it('falls back to title + container text when Readability.parse returns null', async () => {
    // Patch Readability.parse to force the fallback path. Importing
    // and mutating the prototype at test time affects the already-loaded
    // class used by the provider.
    const originalParse = (Readability as any).prototype.parse;
    (Readability as any).prototype.parse = function () {
      return null;
    };
  
    try {
      const html =
        '<html><head><title>Fallback Title</title></head>' +
        '<body><main>Fallback main content</main></body></html>';
      const fetchImpl = vi
        .fn<typeof fetch>()
        .mockResolvedValue(new Response(html, { status: 200, headers: { 'content-type': 'text/html' } }));
      const provider = new LocalFetchURLProvider({ fetchImpl });
  
      const result = await provider.fetch('https://example.com/fallback');
  
      expect(result.kind).toBe('extracted');
      expect(result.content).toBe('# Fallback Title\n\nFallback main content');
    } finally {
      // Restore original behavior to avoid affecting other tests.
      (Readability as any).prototype.parse = originalParse;
    }
  });


  it('rejects private/invalid and unsupported URLs', async () => {
    const fetchImpl = vi.fn<typeof fetch>();
    const provider = new LocalFetchURLProvider({ fetchImpl });
  
    // Invalid URL string
    await expect(provider.fetch('not-a-url')).rejects.toThrow('Invalid URL');
  
    // Unsupported scheme (non-http(s))
    await expect(provider.fetch('ftp://example.com/')).rejects.toThrow('Unsupported URL scheme');
  
    // hostname-based loopback / localhost
    await expect(provider.fetch('http://localhost/')).rejects.toThrow('Refusing to fetch private host');
    await expect(provider.fetch('http://subdomain.localhost/')).rejects.toThrow('Refusing to fetch private host');
  
    // IPv6 loopback literal (bracketed)
    await expect(provider.fetch('http://[::1]/')).rejects.toThrow('Refusing to fetch private host');
  
    // Common private IPv4 ranges (these should be rejected as private addresses)
    await expect(provider.fetch('http://127.0.0.1/')).rejects.toThrow('Refusing to fetch private address');
    await expect(provider.fetch('http://10.0.0.5/')).rejects.toThrow('Refusing to fetch private address');
    await expect(provider.fetch('http://192.168.0.1/')).rejects.toThrow('Refusing to fetch private address');
    // CGNAT range 100.64.0.0/10
    await expect(provider.fetch('http://100.64.0.1/')).rejects.toThrow('Refusing to fetch private address');
  });


  it('throws when no meaningful content can be extracted', async () => {
    const html = '<html><head><title></title></head><body></body></html>';
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(html, { status: 200, headers: { 'content-type': 'text/html' } }));
    const provider = new LocalFetchURLProvider({ fetchImpl });
  
    await expect(provider.fetch('https://example.com/empty')).rejects.toThrow(
      'Failed to extract meaningful content from the page. The page may require JavaScript to render.',
    );
  });


  it('rejects responses exceeding maxBytes via content-length and measured size', async () => {
    // Case A: content-length header too large
    const fetchImplCl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('ok', { status: 200, headers: { 'content-type': 'text/plain', 'content-length': '1000' } }));
    const providerCl = new LocalFetchURLProvider({ fetchImpl: fetchImplCl, maxBytes: 10 });
    await expect(providerCl.fetch('https://example.com/large-cl')).rejects.toThrow('Response body too large');
  
    // Case B: no content-length header, but actual body is too large
    const longBody = 'a'.repeat(50);
    const fetchImplMeasured = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(longBody, { status: 200, headers: { 'content-type': 'text/plain' } }));
    const providerMeasured = new LocalFetchURLProvider({ fetchImpl: fetchImplMeasured, maxBytes: 10 });
    await expect(providerMeasured.fetch('https://example.com/large-measured')).rejects.toThrow('Response body too large');
  });


  it('cancels body and throws on HTTP >= 400', async () => {
    const cancel = vi.fn().mockResolvedValue(undefined);
    const mockResp = {
      status: 500,
      statusText: 'Server Error',
      // headers is not accessed on the error path, but keep a get method for shape
      headers: { get: (_: string) => null },
      body: { cancel },
    };
    const fetchImpl = vi.fn().mockResolvedValue(mockResp as unknown);
    const provider = new LocalFetchURLProvider({ fetchImpl });
  
    await expect(provider.fetch('https://example.com/error')).rejects.toThrow('HTTP 500 Server Error');
    expect(cancel).toHaveBeenCalled();
  });

});
