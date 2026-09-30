let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0008.sanitizeHostBaseEnv', function() {
        it('should not throw and should return an object for empty input object', function() {
            let out;
            assert.doesNotThrow(function() {
                out = testpilot_subject.file_0008.sanitizeHostBaseEnv({});
            }, Error);
            assert.strictEqual(typeof out, 'object');
            assert.notStrictEqual(out, null);
        });
    })
})