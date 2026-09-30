let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    this.timeout(5000);

    it('extractReadableContent should return text + title in text mode for a simple article', async function() {
        const params = {
            html: '<!doctype html><html><head><title>Page Title</title></head><body>' +
                  '<article><h1>Article Heading</h1><p>Hello world!</p></article>' +
                  '</body></html>',
            url: 'https://example.com/article',
            extractMode: 'text'
        };

        const result = await testpilot_subject.file_0006.extractReadableContent(params);
        // Expect a non-null result with text containing both heading and paragraph, and a non-empty title string
        assert.ok(result, 'Expected result to be non-null');
        assert.strictEqual(typeof result.text, 'string', 'Expected text to be a string');
        assert.ok(result.text.indexOf('Article Heading') !== -1, 'Expected text to contain the article heading');
        assert.ok(result.text.indexOf('Hello world') !== -1, 'Expected text to contain the paragraph content');
        assert.strictEqual(typeof result.title, 'string', 'Expected title to be a string');
        assert.ok(result.title.length > 0, 'Expected title to be non-empty');
    });

    })