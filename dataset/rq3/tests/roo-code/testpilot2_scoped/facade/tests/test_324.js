let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a service with controllable internals (no external resources)
    function makeService(initialMessages) {
        const svc = new testpilot_subject.file_0012.MessageQueueService();
        // ensure internal messages array is present and initialized
        svc._messages = Array.isArray(initialMessages) ? initialMessages.slice() : [];

        // Provide a simple findMessage implementation that removeMessage expects
        svc.findMessage = function(id) {
            for (let i = 0; i < this._messages.length; i++) {
                if (this._messages[i] && this._messages[i].id === id) {
                    return { index: i, message: this._messages[i] };
                }
            }
            return { index: -1, message: undefined };
        };

        return svc;
    }

    it('should remove an existing message, return true and emit stateChanged with updated messages', function() {
        const svc = makeService([
            { id: 'a', text: 'first' },
            { id: 'b', text: 'second' }
        ]);

        // capture emits
        const emitted = [];
        svc.emit = function(event, payload) {
            emitted.push({ event, payload });
        };

        const result = svc.removeMessage('a');

        // returns true
        assert.strictEqual(result, true);

        // message removed
        assert.strictEqual(svc._messages.length, 1);
        assert.strictEqual(svc._messages[0].id, 'b');

        // emit called once with stateChanged and the updated messages
        assert.strictEqual(emitted.length, 1);
        assert.strictEqual(emitted[0].event, 'stateChanged');
        // payload should deep-equal the new _messages array
        assert.deepStrictEqual(emitted[0].payload, svc._messages);
    });

    })