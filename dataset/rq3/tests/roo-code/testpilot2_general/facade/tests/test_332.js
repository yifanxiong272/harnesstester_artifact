let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0007.isValidClineMessage', function() {
        it('should return false for non-object or missing message', function(done) {
            const fn = testpilot_subject.file_0007.isValidClineMessage;
            assert.strictEqual(fn(), false);
            assert.strictEqual(fn(null), false);
            assert.strictEqual(fn(123), false);
            assert.strictEqual(fn("string"), false);
            assert.strictEqual(fn(true), false);
            assert.strictEqual(fn(() => {}), false);
            done();
        });

            })
})