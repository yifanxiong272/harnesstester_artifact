let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('onTerminalAttach should ack with INTERNAL_ERROR when terminalHandler is not wired', function(done) {
        // create an instance without running constructor
        const WsProto = testpilot_subject.file_0006.WsConnection.prototype;
        const ws = Object.create(WsProto);

        let sent = null;
        ws.send = function(arg) {
            sent = arg;
        };

        // call the method
        const msg = { id: 123, payload: { /* empty payload is fine */ } };
        ws.onTerminalAttach(msg);

        // the implementation sends synchronously in this branch, so we can assert immediately
        assert.ok(sent, 'send was not called');
        const s = JSON.stringify(sent);
        // The error message "terminal handler not wired" should be included in the ack produced by buildAck
        assert.ok(s.includes('terminal handler not wired'), 'expected error message not found in ack');
        done();
    });

    })