let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.parseImageDimensionError;

    it('returns null for falsy/raw-empty inputs', function() {
        assert.strictEqual(fn(null), null);
        assert.strictEqual(fn(undefined), null);
        // empty string does not contain the trigger phrase -> null
        assert.strictEqual(fn(''), null);
    });

    })