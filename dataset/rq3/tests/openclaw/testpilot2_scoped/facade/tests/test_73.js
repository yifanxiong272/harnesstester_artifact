let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const target = testpilot_subject.file_0001;
    let originalIsFailoverErrorMessage;

    before(function() {
        // Save original to restore later
        originalIsFailoverErrorMessage = target.isFailoverErrorMessage;
    });

    after(function() {
        // Restore original implementation
        target.isFailoverErrorMessage = originalIsFailoverErrorMessage;
    });

    it('returns false for null or undefined message', function() {
        assert.strictEqual(target.isFailoverAssistantError(undefined), false);
        assert.strictEqual(target.isFailoverAssistantError(null), false);
    });

    })