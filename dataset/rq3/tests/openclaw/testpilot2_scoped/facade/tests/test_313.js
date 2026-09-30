let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Allow a bit more time in case async processing is slow
    this.timeout(5000);

    it('sanitizeContentBlocksImages should resolve for empty blocks', async function() {
        let blocks = [];
        let label = 'test-label';
        let opts = {};
        let result = await testpilot_subject.file_0012.sanitizeContentBlocksImages(blocks, label, opts);
        // The function should resolve and return a value (typically an array or object)
        assert.ok(typeof result !== 'undefined' && result !== null, 'expected a non-null/undefined result');
    });

    })