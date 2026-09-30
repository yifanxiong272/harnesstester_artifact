let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0015.stripRedundantSubsystemPrefixForConsole', function() {
        it('should remove "subsystem: " prefix when it matches displaySubsystem', function(done) {
            let message = 'alpha: hello world';
            let displaySubsystem = 'alpha';
            let out = testpilot_subject.file_0015.stripRedundantSubsystemPrefixForConsole(message, displaySubsystem);
            assert.strictEqual(out, 'hello world');
            done();
        });

            })
})