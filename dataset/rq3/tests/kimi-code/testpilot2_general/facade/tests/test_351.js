let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call the prototype method with a fake "this"
    async function callSyncSessions(fakeThis, sessionIds, cursors) {
        return await testpilot_subject.file_0006.WsConnection.prototype.syncSessions.call(fakeThis, sessionIds, cursors);
    }

    it('subscribes to sessionIds and returns accepted and serverCursors when no cursors provided', async function() {
        // Prepare fake "this"
        const calls = { subscribed: [], sent: [], warned: [] };
        const fakeThis = {
            subscriptions: new Set(),
            cursorsBySession: new Map(),
            subscribe: function(sid) { this.subscriptions.add(sid); calls.subscribed.push(sid); },
            send: function(msg) { calls.sent.push(msg); },
            logger: { warn: (obj, msg) => calls.warned.push({obj, msg}) },
            wsBroadcast: {
                // getBufferedSince won't be called in this scenario
                getBufferedSince: async () => { throw new Error('should not be called'); },
                // getCursor will be called for each accepted session
                getCursor: async function(sid) { return `serverCursor-${sid}`; }
            }
        };

        const sessionIds = ['s1', 's2'];
        const result = await callSyncSessions(fakeThis, sessionIds, null);

        // accepted should mirror the provided sessionIds
        assert.deepStrictEqual(result.accepted, ['s1', 's2']);
        // resyncRequired empty
        assert.deepStrictEqual(result.resyncRequired, []);
        // serverCursors should contain values returned by getCursor
        assert.deepStrictEqual(result.serverCursors, { s1: 'serverCursor-s1', s2: 'serverCursor-s2' });
        // subscribe should have been called for both
        assert.deepStrictEqual(calls.subscribed.sort(), ['s1','s2']);
        // no messages should have been sent
        assert.deepStrictEqual(calls.sent, []);
        // no warnings
        assert.deepStrictEqual(calls.warned, []);
    });

    })