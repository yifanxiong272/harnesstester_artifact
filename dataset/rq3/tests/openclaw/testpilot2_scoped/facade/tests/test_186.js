let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to normalize various possible return shapes from extractReadableContent
    function extractTextFromResult(res) {
        if (res == null) return '';
        if (typeof res === 'string') return res;
        if (typeof res === 'object') {
            // common keys that might contain readable content
            const candidates = ['content', 'text', 'excerpt', 'readable', 'html'];
            for (let k of candidates) {
                if (typeof res[k] === 'string') return res[k];
            }
            // If object has a "document" or "body" with text
            if (res.document && typeof res.document === 'string') return res.document;
            if (res.body && typeof res.body === 'string') return res.body;
            // fallback: try JSON stringification
            try { return JSON.stringify(res); } catch(e) { return ''; }
        }
        // any other types
        return String(res);
    }

    it('extractReadableContent should extract plain visible text from simple HTML', async function() {
        const params = {
            // using a simple self-contained HTML string
            html: `
                <!doctype html>
                <html>
                  <head>
                    <title>Sample Title</title>
                    <style>body { color: red; }</style>
                    <script>console.log("nope")</script>
                  </head>
                  <body>
                    <article>
                      <h1>Hello World</h1>
                      <p>This is a <strong>test</strong> of readable extraction.</p>
                    </article>
                    <footer>Footer text</footer>
                  </body>
                </html>
            `
        };

        const res = await testpilot_subject.file_0006.extractReadableContent(params);
        const text = extractTextFromResult(res);

        // Should contain the visible textual content, but not script/style text.
        assert.ok(typeof text === 'string' && text.length > 0, 'result should be a non-empty string or contain text');
        assert.ok(text.includes('Hello World') || text.includes('Hello') , 'should include the H1 text');
        assert.ok(text.includes('test') || text.includes('readable'), 'should include paragraph text');
        // Should not include script content
        assert.ok(!text.includes('console.log'), 'script content should not be present in extracted text');
    });

    })