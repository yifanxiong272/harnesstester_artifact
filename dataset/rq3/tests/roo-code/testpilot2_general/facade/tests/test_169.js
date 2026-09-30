let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0004.PromptManager.prototype.isActive', function() {
        it('should have isActive defined as a function on the prototype', function() {
            // Ensure the module and prototype exist
            assert.ok(testpilot_subject, 'testpilot_subject module is required');
            assert.ok(testpilot_subject.file_0004, 'file_0004 should exist on testpilot_subject');
            assert.ok(testpilot_subject.file_0004.PromptManager, 'PromptManager should exist');
            const proto = testpilot_subject.file_0004.PromptManager.prototype;
            assert.ok(proto, 'PromptManager.prototype should exist');
            assert.strictEqual(typeof proto.isActive, 'function', 'isActive should be a function');
        });

            })
})