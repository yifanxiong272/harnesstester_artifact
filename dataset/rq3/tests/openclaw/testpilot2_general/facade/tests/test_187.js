let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0006.extractReadableContent', function() {
    // Some readability/parsing may take a little time in CI environments.
    this.timeout(5000);

    it('returns text and title for a simple article HTML (default mode)', async function() {
        const html = `
            <!doctype html>
            <html>
              <head><meta charset="utf-8"><title>My Title</title></head>
              <body>
                <article>
                  <h1>Article heading</h1>
                  <p>Hello world</p>
                </article>
              </body>
            </html>
        `;

        const res = await testpilot_subject.file_0006.extractReadableContent({
            html,
            url: 'http://example.com/article/1'
            // extractMode omitted to test default behavior
        });

        // Expect a non-null result with a title and text containing the paragraph content.
        assert.ok(res, 'expected a non-null result');
        assert.strictEqual(res.title, 'My Title', 'expected title to be extracted');
        assert.ok(typeof res.text === 'string' && /Hello\s*world/i.test(res.text), 'expected text to contain "Hello world"');
    });

    })