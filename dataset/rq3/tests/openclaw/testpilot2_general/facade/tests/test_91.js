let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isFailoverAssistantError', function() {
        const fn = testpilot_subject.file_0001.isFailoverAssistantError;

        it('exists and is a function', function() {
            assert.ok(fn, 'function is defined');
            assert.strictEqual(typeof fn, 'function');
        });

            })
})