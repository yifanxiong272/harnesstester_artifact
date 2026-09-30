let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.isFailoverAssistantError', function() {
    const mod = testpilot_subject.file_0001;

    it('returns false for null or undefined message', function() {
        assert.strictEqual(mod.isFailoverAssistantError(null), false);
        assert.strictEqual(mod.isFailoverAssistantError(undefined), false);
    });

    })