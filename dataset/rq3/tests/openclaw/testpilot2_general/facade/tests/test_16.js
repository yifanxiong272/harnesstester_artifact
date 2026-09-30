let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    it('returns undefined when there is no errorMessage and stopReason is not "error"', function() {
        const msg = { stopReason: 'completed' }; // no errorMessage
        const res = testpilot_subject.file_0001.formatAssistantErrorText(msg);
        assert.strictEqual(res, undefined);
    });

    })