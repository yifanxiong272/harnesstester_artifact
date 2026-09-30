let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0023.mergeConsecutiveApiMessages', function() {
        it('should return an array for empty input', function() {
            let res = testpilot_subject.file_0023.mergeConsecutiveApiMessages([], {});
            assert.ok(Array.isArray(res), 'result should be an array');
            assert.strictEqual(res.length, 0, 'empty input should produce empty output');
        });

            })
})