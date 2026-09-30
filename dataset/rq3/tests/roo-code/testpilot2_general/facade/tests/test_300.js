let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const handle = testpilot_subject.file_0007.MessageProcessor.prototype.handleStateMessage;

    function makeSpy() {
        const calls = [];
        const fn = function() {
            calls.push(Array.from(arguments));
        };
        fn.calls = calls;
        return fn;
    }

    it('returns early when message has no state (does not call store/emitter methods)', function() {
        const store = {
            getCurrentMode: () => { throw new Error('getCurrentMode should not be called'); },
            setCurrentMode: () => { throw new Error('setCurrentMode should not be called'); },
            getAgentState: () => { throw new Error('getAgentState should not be called'); },
            setMessages: () => { throw new Error('setMessages should not be called'); }
        };
        const emitter = {
            emit: () => { throw new Error('emitter.emit should not be called'); }
        };
        const context = {
            options: { debug: true },
            store,
            emitter,
            emitStateChangeEvents: () => { throw new Error('emitStateChangeEvents should not be called'); },
            emitNewMessageEvents: () => { throw new Error('emitNewMessageEvents should not be called'); }
        };

        // Should not throw; should simply return
        handle.call(context, {});
    });

    })