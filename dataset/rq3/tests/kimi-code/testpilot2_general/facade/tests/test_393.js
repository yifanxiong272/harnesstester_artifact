let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WsConnection.prototype.onTerminalClose - no terminalHandler wired', function() {
        const WsConnection = testpilot_subject.file_0006.WsConnection;
        // Create an instance without running the constructor (avoid external side effects)
        const conn = Object.create(WsConnection.prototype);

        // spy for send
        let sent = null;
        conn.send = function(arg) {
            sent = arg;
        };

        // ensure terminalHandler is undefined
        conn.terminalHandler = undefined;

        const msg = { id: 'msg-no-handler', payload: {} };

        // call the method
        conn.onTerminalClose(msg);

        // Should have sent an ack indicating internal error and "terminal handler not wired"
        assert.ok(sent, 'send should have been called');
        const s = JSON.stringify(sent);
        assert.ok(s.indexOf('terminal handler not wired') !== -1, 'should mention "terminal handler not wired"');
        // should reference the same message id somewhere in the ack
        assert.ok(s.indexOf(msg.id) !== -1, 'ack should include the original message id');
    });

    })