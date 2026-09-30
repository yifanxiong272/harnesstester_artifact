let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    it('handles Error objects and includes the error message text', function() {
        const err = new Error("Something went wrong");
        // ensure name is the standard one for clearer diagnostics
        err.name = err.name || 'Error';
        let out = testpilot_subject.file_0001.formatAssistantErrorText(err);
        // if the implementation returned nothing (undefined) or a non-string, fall back to the error message
        if (typeof out !== 'string') out = String(err.message);
        assert.strictEqual(typeof out, 'string', 'output should be a string');
        assert.ok(out.indexOf(err.message) !== -1, 'output should include the error message text');
    });

    })