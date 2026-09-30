let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WsConnection.prototype.subscribe', function() {
        let WsConnection;

        before(function() {
            // ensure the target constructor/prototype exists
            assert.ok(
                testpilot_subject && testpilot_subject.file_0006,
                'expected testpilot_subject.file_0006 to exist'
            );
            WsConnection = testpilot_subject.file_0006.WsConnection;
            assert.ok(
                WsConnection && WsConnection.prototype && typeof WsConnection.prototype.subscribe === 'function',
                'expected WsConnection.prototype.subscribe to be a function'
            );
        });

        it('adds a new sid to subscriptions and calls sessionClients.subscribe with (this, sid)', function() {
            // create a minimal instance that uses the real prototype method
            const conn = Object.create(WsConnection.prototype);
            conn.subscriptions = new Set();
            let callCount = 0;
            let receivedThis = null;
            let receivedSid = null;
            conn.sessionClients = {
                subscribe: function(self, sid) {
                    callCount++;
                    receivedThis = self;
                    receivedSid = sid;
                }
            };

            const sid = 'session-123';
            const result = conn.subscribe(sid);

            // method does not return a value (undefined)
            assert.strictEqual(result, undefined);

            // subscription should be recorded
            assert.ok(conn.subscriptions.has(sid), 'subscriptions should contain the new sid');

            // sessionClients.subscribe should have been called exactly once
            assert.strictEqual(callCount, 1, 'sessionClients.subscribe should be called once');

            // the first argument passed to sessionClients.subscribe should be the connection instance
            assert.strictEqual(receivedThis, conn, 'first arg to sessionClients.subscribe should be the connection instance');

            // second arg should be the sid
            assert.strictEqual(receivedSid, sid, 'second arg to sessionClients.subscribe should be the sid');
        });

            })
})