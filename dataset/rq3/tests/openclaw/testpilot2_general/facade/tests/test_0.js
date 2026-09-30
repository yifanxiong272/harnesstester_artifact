let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0001, 'file_0001 should be present on testpilot_subject');
            assert.strictEqual(typeof testpilot_subject.file_0001.classifyFailoverReason, 'function',
                'classifyFailoverReason should be a function');
        });

            })
})