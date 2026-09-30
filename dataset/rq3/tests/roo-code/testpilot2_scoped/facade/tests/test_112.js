let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0010.CacheStrategy.prototype.meetsMinTokenThreshold', function() {
    const method = testpilot_subject.file_0010.CacheStrategy.prototype.meetsMinTokenThreshold;

    it('returns false when minTokensPerCachePoint is undefined', function() {
        const ctx = { config: { modelInfo: { minTokensPerCachePoint: undefined } } };
        const result = method.call(ctx, 10);
        assert.strictEqual(result, false);
    });

    })