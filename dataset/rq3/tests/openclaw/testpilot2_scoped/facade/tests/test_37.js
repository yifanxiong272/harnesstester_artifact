let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isAuthAssistantError', function() {
        it('returns false for falsy msg (null)', function(done) {
            const fn = testpilot_subject.file_0001.isAuthAssistantError;
            assert.strictEqual(fn(null), false);
            assert.strictEqual(fn(undefined), false);
            done();
        });

            })
})