let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
        let fn = testpilot_subject &&
                 testpilot_subject.file_0001 &&
                 testpilot_subject.file_0001.classifyFailoverReason;

        it('should be present and be a function', function() {
            assert.ok(fn, 'classifyFailoverReason should be defined');
            assert.strictEqual(typeof fn, 'function', 'classifyFailoverReason should be a function');
        });

            })
})