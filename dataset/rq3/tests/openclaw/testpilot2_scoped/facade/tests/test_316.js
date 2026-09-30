let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.sanitizeImageBlocks', function() {
    it('returns empty images and dropped 0 when input array is empty', async function() {
        const res = await testpilot_subject.file_0012.sanitizeImageBlocks([], 'label-for-empty');
        assert.strictEqual(typeof res, 'object');
        assert.deepStrictEqual(res.images, []);
        assert.strictEqual(res.dropped, 0);
    });

    })