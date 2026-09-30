let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0012.extractToolCallsFromAssistant', function() {
        const fn = testpilot_subject.file_0012 && testpilot_subject.file_0012.extractToolCallsFromAssistant;

        it('should exist and be a function', function() {
            assert.ok(fn, 'function is not exported');
            assert.strictEqual(typeof fn, 'function');
        });

            })
})