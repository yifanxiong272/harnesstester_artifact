let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('calls send when onUnsubscribe is invoked (basic behavior)', function() {
        let proto = testpilot_subject.file_0006.WsConnection.prototype;
        // create a plain object whose prototype is the real prototype so that onUnsubscribe uses the same code
        let conn = Object.create(proto);
        // stub send to record that it was called and with what
        conn._sent = null;
        conn.send = function(msg) { conn._sent = msg; };

        // call with a minimal unsubscribe message that includes payload.session_ids
        let msg = { id: 12345, payload: { session_ids: [] } };
        // Should not throw
        proto.onUnsubscribe.call(conn, msg);

        // Ensure send was called at least once (implementation should respond to unsubscribe)
        assert.ok(conn._sent !== null, 'expected send to be called when unsubscribing');
    });

});