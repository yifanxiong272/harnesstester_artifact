let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.convertToAiSdkMessages', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject.file_0015, 'file_0015 should be present on testpilot_subject');
            assert.strictEqual(typeof testpilot_subject.file_0015.convertToAiSdkMessages, 'function',
                'convertToAiSdkMessages should be a function');
        });

            })
})