let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0011.stripRedundantSubsystemPrefixForConsole;

    it('does not mangle messages that have no subsystem prefix', function() {
        const msg = 'Just a plain message without prefixes';
        // pass an empty string for displaySubsystem so toLowerCase can be called safely
        const out = fn(msg, '');
        // At minimum the meaningful portion of the message should remain present
        assert.strictEqual(typeof out, 'string');
        assert.ok(out.includes('plain message'), 'expected message content to be preserved when there is no subsystem prefix');
    });
});