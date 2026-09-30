let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const closeFn = testpilot_subject.file_0006.WsConnection.prototype.close;

    it('calls socket.close with default code 1000 and undefined reason when no args are provided', function(done) {
        let called = 0;
        let receivedArgs = null;
        const socket = {
            close(code, reason) {
                called++;
                receivedArgs = [code, reason];
            }
        };
        const ctx = { closed: false, socket: socket };

        // invoke the prototype method with our fake this
        closeFn.call(ctx);

        assert.strictEqual(called, 1, 'socket.close should be called once');
        assert.strictEqual(receivedArgs[0], 1000, 'default code should be 1000');
        assert.strictEqual(receivedArgs[1], undefined, 'default reason should be undefined');
        done();
    });

    })