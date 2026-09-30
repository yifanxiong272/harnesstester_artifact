let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.PromptManager.prototype.promptForInput', function() {
        it('should exist and be a function on the prototype', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module is present');
            const file0004 = testpilot_subject.file_0004;
            assert.ok(file0004, 'file_0004 namespace is present');
            const PromptManager = file0004.PromptManager;
            assert.ok(PromptManager, 'PromptManager is exported');
            assert.strictEqual(typeof PromptManager.prototype.promptForInput, 'function', 'promptForInput should be a function on the prototype');
        });

            })
})