let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0005.convertToBedrockConverseMessages', function() {
        it('should be a function', function() {
            assert.ok(testpilot_subject);
            assert.strictEqual(typeof testpilot_subject.file_0005.convertToBedrockConverseMessages, 'function');
        });

            })
})