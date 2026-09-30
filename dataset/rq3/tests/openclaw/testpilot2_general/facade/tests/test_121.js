let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns false for falsy message', function() {
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(null), false);
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(undefined), false);
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(0), false);
    });

    })