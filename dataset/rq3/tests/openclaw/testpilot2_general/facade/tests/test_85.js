let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.isContextOverflowError', function() {
    const fn = testpilot_subject.file_0001.isContextOverflowError;

    it('returns false for empty / falsy messages', function() {
        assert.strictEqual(fn(undefined), false);
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(''), false);
    });

    })