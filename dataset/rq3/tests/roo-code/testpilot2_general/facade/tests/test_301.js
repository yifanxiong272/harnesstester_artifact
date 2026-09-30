let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0007.MessageProcessor.prototype.handleMessageUpdated', function() {
        it('should exist and be a function on the prototype', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module is available');
            assert.ok(testpilot_subject.file_0007, 'file_0007 namespace is available');
            const MP = testpilot_subject.file_0007.MessageProcessor;
            assert.ok(MP, 'MessageProcessor is present');
            assert.strictEqual(typeof MP.prototype.handleMessageUpdated, 'function', 'handleMessageUpdated should be a function');
        });

            })
})