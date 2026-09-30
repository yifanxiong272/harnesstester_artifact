let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isRateLimitAssistantError', function() {
    const subject = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.isRateLimitAssistantError;
    it('should export the isRateLimitAssistantError function', function() {
        assert.ok(subject, 'isRateLimitAssistantError is not exported at testpilot_subject.file_0001.isRateLimitAssistantError');
        assert.strictEqual(typeof subject, 'function');
    });

    })