let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the prototype method so we can create lightweight instances for testing
    const WsProto = testpilot_subject.file_0006.WsConnection.prototype;

    function makeConn(id) {
        // Create a plain object that inherits the prototype so the method under test can run
        const conn = Object.create(WsProto);
        conn.id = id || 'conn-id-1';
        return conn;
    }

    it('sends an INTERNAL_ERROR ack when terminalHandler is not wired', function() {
        const conn = makeConn('conn-no-handler');

        // capture what send was called with
        let sent = null;
        conn.send = function(arg) { sent = arg; };

        const msg = { id: 'msg-1', payload: { session_id: 's', terminal_id: 't' } };

        // Call the method under test
        conn.onTerminalDetach(msg);

        // Basic expectations: send should have been invoked
        assert.ok(sent, 'expected conn.send to be called with an ack');

        // The implementation uses a buildAck containing the message string "terminal handler not wired".
        // Check that the serialized form contains that phrase to ensure the internal-error branch ran.
        const serialized = (() => {
            try {
                return JSON.stringify(sent);
            } catch (e) {
                // If not JSON-serializable, fall back to toString
                return String(sent);
            }
        })();
        assert.ok(serialized.indexOf('terminal handler not wired') !== -1, 'expected ack to mention "terminal handler not wired"');
    });

    })