let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WsConnection.prototype.unsubscribe', function() {
        it('should do nothing and not call sessionClients.unsubscribe when sid is not subscribed', function(done) {
            // create a plain object whose prototype is the WsConnection prototype
            const proto = testpilot_subject.file_0006.WsConnection.prototype;
            const conn = Object.create(proto);

            // setup subscriptions as an empty Set and a spy sessionClients
            conn.subscriptions = new Set();
            let called = false;
            conn.sessionClients = {
                unsubscribe: function() { called = true; }
            };

            // call unsubscribe for a sid that is not present
            conn.unsubscribe('missing-sid');

            // expectations: subscriptions unchanged and sessionClients.unsubscribe not called
            assert.strictEqual(conn.subscriptions.size, 0);
            assert.strictEqual(called, false);
            done();
        });

            })
})