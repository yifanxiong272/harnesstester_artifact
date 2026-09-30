let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0017.buildBootstrapPromptWarning', function() {
        it('should exist and be a function', function() {
            assert.ok(testpilot_subject, 'module testpilot_subject should be present');
            assert.ok(testpilot_subject.file_0017, 'file_0017 namespace should be present');
            assert.strictEqual(typeof testpilot_subject.file_0017.buildBootstrapPromptWarning, 'function',
                'buildBootstrapPromptWarning should be a function');
        });

            })
})