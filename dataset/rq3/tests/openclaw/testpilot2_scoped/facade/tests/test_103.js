let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isMissingToolCallInputError', function() {
    const fn = testpilot_subject.file_0001.isMissingToolCallInputError;

    it('returns false for falsy inputs', function() {
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
        assert.strictEqual(fn(''), false);
        // function uses if(!raw) so other falsy values should also return false
        assert.strictEqual(fn(0), false);
        assert.strictEqual(fn(false), false);
    });

    })