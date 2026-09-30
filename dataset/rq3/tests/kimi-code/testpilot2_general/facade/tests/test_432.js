let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const closeFn = testpilot_subject.file_0006.WsConnection.prototype.close;

    it('calls socket.close with default code (1000) and undefined reason when none provided', function() {
        let called = false;
        let receivedCode = undefined;
        let receivedReason = undefined;

        const fakeSocket = {
            close(code, reason) {
                called = true;
                receivedCode = code;
                receivedReason = reason;
            }
        };

        const ctx = { socket: fakeSocket, closed: false };

        // invoke the prototype method with no args => should use default 1e3 (1000)
        closeFn.call(ctx);

        assert.strictEqual(called, true, 'socket.close should have been called');
        assert.strictEqual(receivedCode, 1000, 'default close code should be 1000');
        assert.strictEqual(receivedReason, undefined, 'default reason should be undefined');
    });

    })