let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    const fn = testpilot_subject.file_0001.formatAssistantErrorText;

    it('returns undefined when no error message and stopReason is not "error"', function() {
        const msg = { errorMessage: "", stopReason: "user", model: "m" };
        const out = fn(msg, {});
        assert.strictEqual(out, undefined);
    });

    })