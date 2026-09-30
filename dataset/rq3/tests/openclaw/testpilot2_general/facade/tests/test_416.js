let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0014.isToolResultError', function() {
        let fn = testpilot_subject && testpilot_subject.file_0014 && testpilot_subject.file_0014.isToolResultError;

        it('should export a function', function() {
            assert.ok(fn, 'function isToolResultError is missing');
            assert.strictEqual(typeof fn, 'function');
        });

            })
})