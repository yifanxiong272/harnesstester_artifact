let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    const format = testpilot_subject.file_0001.formatAssistantErrorText;

    it('is deterministic for the same input (multiple calls produce identical output)', function() {
        const msg = 'deterministic check';
        const a = format(msg);
        const b = format(msg);
        assert.strictEqual(a, b, 'format should return the same string for the same input on repeated calls');
    });
});