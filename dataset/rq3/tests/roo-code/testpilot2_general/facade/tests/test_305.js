let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0007.MessageProcessor.prototype.handleInvoke - exists and is function', function() {
        // Ensure the module and path exist
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');

        // Navigate to the constructor/prototype
        let MessageProcessor;
        if (testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor) {
            MessageProcessor = testpilot_subject.file_0007.MessageProcessor;
        } else {
            // Provide clearer error if path isn't present
            assert.fail('testpilot_subject.file_0007.MessageProcessor is not defined');
        }

        // The prototype should have the handleInvoke property
        assert.ok(MessageProcessor.prototype.hasOwnProperty('handleInvoke'),
            'MessageProcessor.prototype should have handleInvoke');

        const handleInvoke = MessageProcessor.prototype.handleInvoke;
        assert.strictEqual(typeof handleInvoke, 'function', 'handleInvoke should be a function');
    });

    })