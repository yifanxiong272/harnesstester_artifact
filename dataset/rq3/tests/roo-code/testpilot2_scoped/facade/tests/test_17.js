let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.getEffectiveApiHistory', function() {
        it('returns an empty array for empty input', function(done) {
            let result = testpilot_subject.file_0004.getEffectiveApiHistory([]);
            assert.ok(Array.isArray(result), 'result should be an array');
            assert.strictEqual(result.length, 0, 'result array should be empty');
            done();
        });

            })
})