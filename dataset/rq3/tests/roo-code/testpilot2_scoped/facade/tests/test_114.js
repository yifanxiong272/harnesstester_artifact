let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0010.CacheStrategy.prototype.estimateTokenCount', function() {
    const estimate = testpilot_subject.file_0010.CacheStrategy.prototype.estimateTokenCount;

    it('returns 0 when message has no content (undefined)', function() {
        const message = {};
        const result = estimate.call({}, message);
        assert.strictEqual(result, 0);
    });

    })