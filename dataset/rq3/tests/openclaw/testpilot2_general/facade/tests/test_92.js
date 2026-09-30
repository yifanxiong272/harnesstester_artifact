let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isFailoverAssistantError;

    it('returns false for falsy message values', function() {
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
        // also test an empty object (no stopReason)
        assert.strictEqual(fn({}), false);
    });

    })