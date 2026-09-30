let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const sendFn = testpilot_subject.file_0006.WsConnection.prototype.send;

    it('does not call socket.send when connection is closed', function() {
        let called = false;
        const ctx = {
            closed: true,
            socket: {
                OPEN: 1,
                readyState: 1,
                send: function() { called = true; }
            },
            logger: { warn: function() { /* noop */ } }
        };

        sendFn.call(ctx, { hello: 'world' });
        assert.strictEqual(called, false, 'socket.send should not be called when closed === true');
    });

    })