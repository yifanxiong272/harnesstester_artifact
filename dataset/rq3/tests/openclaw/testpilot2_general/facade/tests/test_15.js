let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.formatAssistantErrorText', function() {
    it('is deterministic for the same inputs (calling twice yields same result)', function() {
        const msg = "determinism check";
        const opts = { foo: 'bar', verbose: false };
        const out1 = testpilot_subject.file_0001.formatAssistantErrorText(msg, opts);
        const out2 = testpilot_subject.file_0001.formatAssistantErrorText(msg, opts);
        assert.strictEqual(out1, out2, 'function should return the same string for identical inputs');
    });

    })