let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a WsConnection-like instance that uses the real prototype method
    function createWsInstance(overrides = {}) {
        const proto = testpilot_subject.file_0006.WsConnection.prototype;
        const ws = Object.create(proto);

        // simple spies / stubs
        ws.sent = [];
        ws.send = function(arg) { ws.sent.push(arg); };

        ws.logger = {
            infoCalls: [],
            warnCalls: [],
            info: function(...args){ this.infoCalls.push(args); }.bind(ws.logger || {}),
            warn: function(...args){ this.warnCalls.push(args); }.bind(ws.logger || {})
        };
        // Replace logger methods to capture on the ws.logger object
        ws.logger = {
            infoCalls: [],
            warnCalls: [],
            info: function(...args){ ws.logger.infoCalls.push(args); },
            warn: function(...args){ ws.logger.warnCalls.push(args); }
        };

        // default syncSessions stub
        ws.syncCalled = [];
        ws.syncSessions = async function(session_ids, cursors){
            ws.syncCalled.push([session_ids, cursors]);
            return {
                accepted: ['accepted-session'],
                serverCursors: { foo: 'bar' },
                resyncRequired: false
            };
        };

        // default fsWatchHandler (may be overridden)
        ws.fsWatchHandler = undefined;

        // id used when adding watch fs
        ws.id = overrides.id || 'client-1';

        // apply overrides
        Object.assign(ws, overrides);

        return ws;
    }

    it('onSubscribe: calls syncSessions and sends ack containing sync results when no watch_fs', async function() {
        const ws = createWsInstance();
        // craft message without watch_fs
        const msg = {
            id: 'msg-1',
            payload: {
                session_ids: ['s1','s2'],
                cursors: { s1: 1, s2: 2 }
            }
        };

        // call the method
        await ws.onSubscribe(msg);

        // syncSessions was called with the provided session_ids and cursors
        assert.strictEqual(ws.syncCalled.length, 1, 'syncSessions should be called once');
        assert.deepStrictEqual(ws.syncCalled[0][0], msg.payload.session_ids);
        assert.deepStrictEqual(ws.syncCalled[0][1], msg.payload.cursors);

        // send was called once with some ack object. We assert it includes the sync values.
        assert.strictEqual(ws.sent.length, 1, 'send should be called once');
        const sentStr = JSON.stringify(ws.sent[0]);
        // check for accepted, cursors and resync_required presence in the serialized ack
        assert.ok(sentStr.indexOf('"accepted"') !== -1, 'ack should include accepted');
        assert.ok(sentStr.indexOf('accepted-session') !== -1, 'accepted value should be present');
        assert.ok(sentStr.indexOf('"cursors"') !== -1, 'ack should include cursors');
        assert.ok(sentStr.indexOf('"resync_required"') !== -1 || sentStr.indexOf('resyncRequired') !== -1,
                  'ack should include resync_required (or resyncRequired) field');

        // logger.info should have been called
        assert.ok(ws.logger.infoCalls.length >= 1, 'logger.info should be called at least once');
    });

    })