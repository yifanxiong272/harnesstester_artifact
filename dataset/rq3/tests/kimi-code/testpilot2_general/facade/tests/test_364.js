let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('does not throw when unsubscribing from an unknown topic', function() {
        let proto = testpilot_subject.file_0006.WsConnection.prototype;
        let conn = Object.create(proto);

        // no subscriptions set up at all
        conn._sent = null;
        conn.send = function(msg) { conn._sent = msg; };

        // Unsubscribe from a topic that doesn't exist
        // Include an empty payload so destructuring (e.g. payload.session_ids) won't fail
        let msg = { id: 99, topic: 'non-existent-topic', payload: { session_ids: [] } };

        // Should not throw
        proto.onUnsubscribe.call(conn, msg);

        // Implementation should handle gracefully and likely call send; at minimum it shouldn't throw
        assert.ok(true);
    });
});