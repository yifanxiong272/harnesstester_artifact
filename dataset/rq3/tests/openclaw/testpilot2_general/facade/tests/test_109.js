let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isLikelyContextOverflowError;

    it('returns false for empty / falsy input', function() {
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
        assert.strictEqual(fn(''), false);
    });

    })