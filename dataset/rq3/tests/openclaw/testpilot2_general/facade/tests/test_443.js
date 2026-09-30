let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0015.stripRedundantSubsystemPrefixForConsole;

    it('returns original message when displaySubsystem is falsy', function(done) {
        const msg = "Some message";
        assert.strictEqual(fn(msg, undefined), msg);
        assert.strictEqual(fn(msg, null), msg);
        assert.strictEqual(fn(msg, ""), msg);
        done();
    });

    })