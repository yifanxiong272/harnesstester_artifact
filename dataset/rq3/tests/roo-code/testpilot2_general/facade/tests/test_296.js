let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0007.MessageProcessor.prototype.processMessage', function() {
    // Helper to call the prototype method with a fake "this"
    const processMessage = testpilot_subject.file_0007.MessageProcessor.prototype.processMessage;

    it('calls handleStateMessage when message.type === "state"', function() {
        let called = false;
        const message = { type: 'state', foo: 'bar' };
        const fakeThis = {
            options: { debug: false },
            handleStateMessage: function(m) {
                called = true;
                // ensure the same message object was forwarded
                assert.strictEqual(m, message);
            },
            // other handlers should not be called in this test
            handleMessageUpdated: function() { throw new Error('should not be called'); },
            handleAction: function() { throw new Error('should not be called'); },
            handleInvoke: function() { throw new Error('should not be called'); },
            emitter: { emit: function() {} }
        };

        processMessage.call(fakeThis, message);
        assert.ok(called, 'handleStateMessage was not called');
    });

    })