let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('test testpilot_subject.file_0017.convertToMistralMessages', function() {
        it('returns an empty array when given an empty array', function(done) {
            let convert = testpilot_subject.file_0017.convertToMistralMessages;
            // empty input should produce an empty array (no side effects)
            let res = convert([]);
            assert(Array.isArray(res), 'result should be an array');
            assert.strictEqual(res.length, 0, 'result array should be empty');
            done();
        });

            })
})