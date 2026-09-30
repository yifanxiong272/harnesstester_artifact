let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0007.MessageProcessor.prototype.processMessages', function() {
        let MessageProcessor;
        let instance;

        before(function() {
            // Ensure the constructor exists on the provided module
            MessageProcessor = testpilot_subject &&
                              testpilot_subject.file_0007 &&
                              testpilot_subject.file_0007.MessageProcessor;
            if (!MessageProcessor) {
                throw new Error('MessageProcessor constructor not found on testpilot_subject.file_0007');
            }
        });

        beforeEach(function() {
            instance = new MessageProcessor();
        });

        it('should have a processMessages function on the prototype', function() {
            assert.ok(typeof MessageProcessor.prototype.processMessages === 'function',
                      'processMessages should be a function on the prototype');
            assert.ok(typeof instance.processMessages === 'function',
                      'processMessages should be available on an instance');
        });

            })
})