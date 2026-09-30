let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isServerErrorMessage', function() {
        it('returns true for "500 Internal Server Error"', function(done) {
            let raw = "500 Internal Server Error";
            let result = testpilot_subject.file_0001.isServerErrorMessage(raw);
            assert.strictEqual(result, true);
            done();
        });

            })
})