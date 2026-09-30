let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0001.isBillingAssistantError;

    it('returns false for null or undefined msg', function() {
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
    });

    })