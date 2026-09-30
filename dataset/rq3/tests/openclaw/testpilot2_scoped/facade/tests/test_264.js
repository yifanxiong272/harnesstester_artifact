let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.normalizeNotifyOutput', function() {
        it('collapses multiple spaces into single spaces', function(done) {
            const input = "This   is    a  test";
            const expected = "This is a test";
            const actual = testpilot_subject.file_0008.normalizeNotifyOutput(input);
            assert.strictEqual(actual, expected);
            done();
        });

            })
})