let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a lightweight instance-like object that uses the WsConnection prototype
    function makeConn() {
        const proto = testpilot_subject.file_0006.WsConnection.prototype;
        const conn = Object.create(proto);
        conn._sent = null;
        conn._sendCount = 0;
        conn.send = function(arg) { // capture whatever buildAck produced
            conn._sendCount++;
            conn._sent = arg;
        };
        conn.logger = {
            warned: [],
            warn: function(...args) { this.warned.push(args); }
        };
        // leave abortHandler undefined by default; tests will set it as needed
        return conn;
    }

    // Small helper to stringify the send payload for assertions.
    // If send argument is an object, JSON.stringify is used; otherwise convert to String.
    function sentString(conn) {
        const v = conn._sent;
        try {
            return typeof v === 'string' ? v : JSON.stringify(v);
        } catch (e) {
            // fallback if non-serializable
            return String(v);
        }
    }

    it('sends internal error ack when abortHandler not wired', function(done) {
        const conn = makeConn();
        const msg = { id: 1, payload: { session_id: 's1', prompt_id: 'p1' } };
        conn.onAbort(msg);
        // onAbort will send synchronously in this branch
        setImmediate(() => {
            assert.strictEqual(conn._sendCount, 1, 'send should be called once');
            const s = sentString(conn);
            assert(s.indexOf('abort handler not wired') !== -1, 'should mention "abort handler not wired": ' + s);
            done();
        });
    });

    })