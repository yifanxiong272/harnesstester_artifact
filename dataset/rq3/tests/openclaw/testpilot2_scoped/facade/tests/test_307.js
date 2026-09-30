let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const f = testpilot_subject.file_0011.stripRedundantSubsystemPrefixForConsole;

    it('returns original message when displaySubsystem is falsy', function(done) {
        const msg = "SomeSubsystem: This is a message";
        assert.strictEqual(f(msg, null), msg);
        assert.strictEqual(f(msg, undefined), msg);
        assert.strictEqual(f(msg, ""), msg);
        done();
    });

    })