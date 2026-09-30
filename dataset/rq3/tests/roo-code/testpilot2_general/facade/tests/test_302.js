let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('handleMessageUpdated should do nothing when message.clineMessage is missing (debug off)', function(done) {
        // Arrange: create a lightweight instance that uses the prototype method directly
        const proto = testpilot_subject.file_0007.MessageProcessor.prototype;
        const instance = Object.create(proto);

        // spies / mocks
        let updateMessageCalled = false;
        let getAgentStateCalled = false;
        let emitterEmitCalled = false;

        instance.store = {
            updateMessage: function() { updateMessageCalled = true; },
            getAgentState: function() { getAgentStateCalled = true; return { some: 'state' }; }
        };
        instance.emitter = {
            emit: function() { emitterEmitCalled = true; }
        };
        instance.options = { debug: false };
        instance.emitStateChangeEvents = function() { throw new Error('emitStateChangeEvents should not be called'); };

        // Act
        const result = instance.handleMessageUpdated({}); // message without clineMessage

        // Assert
        assert.strictEqual(result, undefined);
        assert.strictEqual(updateMessageCalled, false, 'store.updateMessage should not be called');
        assert.strictEqual(getAgentStateCalled, false, 'store.getAgentState should not be called');
        assert.strictEqual(emitterEmitCalled, false, 'emitter.emit should not be called');

        done();
    });

    })