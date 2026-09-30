let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Use a bit more time in case some internal helpers are async/slow
    this.timeout(5000);

    it('passes through non-image blocks unchanged', async function() {
        const blocks = [
            { type: 'text', text: 'Hello world' },
            { type: 'custom', value: 42 }
        ];
        const out = await testpilot_subject.file_0012.sanitizeContentBlocksImages(blocks, 'LABEL');
        // Non-image blocks should be passed through (deep equal)
        assert.deepStrictEqual(out, blocks);
    });

    })