let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0011.stripRedundantSubsystemPrefixForConsole;

    it('does not remove the subsystem prefix when displaySubsystem = false', function() {
        const msg = 'Beta: perform task';
        const out = fn(msg, false);
        // When displaySubsystem is false, the subsystem label should remain at the start
        assert.strictEqual(typeof out, 'string');
        assert.ok(out.trim().startsWith('Beta:'), 'expected subsystem prefix to be present when displaySubsystem=false');
    });

    })