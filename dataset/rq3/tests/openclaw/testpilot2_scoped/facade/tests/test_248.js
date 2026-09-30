let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0008.formatExecFailureReason;

    it('returns "Command not found" for shell-command-not-found', function() {
        const out = fn({ failureKind: "shell-command-not-found" });
        assert.strictEqual(out, "Command not found");
    });

    })