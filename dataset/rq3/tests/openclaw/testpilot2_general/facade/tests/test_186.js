let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to extract a string from whatever the implementation returns
    function extractStringFromResult(res) {
        if (res == null) return null;
        if (typeof res === 'string') return res;
        if (typeof res === 'object') {
            // common property names that an "extractReadableContent" might return
            for (let key of ['content', 'text', 'readableText', 'readable', 'html', 'body']) {
                if (typeof res[key] === 'string') return res[key];
            }
            // sometimes the object itself may have a toString
            if (typeof res.toString === 'function') {
                try {
                    let s = res.toString();
                    if (typeof s === 'string' && s.length > 0) return s;
                } catch (e) { /* ignore */ }
            }
        }
        return null;
    }

    it('should extract readable text from a simple HTML input', async function() {
        // do not use any external resources; provide the HTML directly
        let params = { html: '<html><head><title>t</title></head><body><article><p>Hello World</p></article></body></html>' };
        let result = await testpilot_subject.file_0006.extractReadableContent(params);
        let text = extractStringFromResult(result);
        assert.ok(text !== null, 'expected a string or object with text content');
        assert.ok(text.indexOf('Hello') !== -1 || text.indexOf('World') !== -1,
            'expected extracted text to include "Hello" or "World", got: ' + String(text));
    });

    })