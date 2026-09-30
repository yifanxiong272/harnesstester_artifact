let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // A basic happy-path test: ensures gotClientHello is set, syncSessions is called with the payload,
    // logger.info is called with the counts, and send is invoked.
    it('test testpilot_subject.file_0006.WsConnection.prototype.onClientHello - basic behavior', async function() {
        const proto = testpilot_subject.file_0006.WsConnection.prototype;
        // Create an instance-like object that uses the real prototype methods.
        const ws = Object.create(proto);
        ws.gotClientHello = false;

        // Stub syncSessions to verify it receives the payload and to return a known result.
        let syncCalled = false;
        let receivedSyncArgs = null;
        ws.syncSessions = async (subscriptions, cursors) => {
            syncCalled = true;
            receivedSyncArgs = { subscriptions, cursors };
            return {
                accepted: ['sub-a', 'sub-b'],
                resyncRequired: ['sub-x'],
                serverCursors: { room: 'cursor123' }
            };
        };

        // Stub logger.info to capture its arguments.
        let logged = null;
        ws.logger = {
            info: (obj, msg) => {
                logged = { obj, msg };
            }
        };

        // Stub send to capture what is sent.
        let sent = null;
        ws.send = (arg) => { sent = arg; };

        const msg = {
            id: 42,
            payload: {
                subscriptions: ['sub-a', 'sub-b'],
                cursors: { room: 'cursor123' }
            }
        };

        await ws.onClientHello(msg);

        // Assertions
        assert.strictEqual(ws.gotClientHello, true, 'gotClientHello should be set to true');
        assert.strictEqual(syncCalled, true, 'syncSessions should have been called');
        assert.deepStrictEqual(receivedSyncArgs, { subscriptions: msg.payload.subscriptions, cursors: msg.payload.cursors });
        assert.ok(logged, 'logger.info should have been called');
        assert.deepStrictEqual(logged.obj, { acceptedCount: 2, resyncRequiredCount: 1 });
        assert.strictEqual(logged.msg, 'client hello');
        assert.ok(sent !== null, 'send should have been called with the ack object');
        // The ack object is produced by an internal buildAck; we at least expect the serverCursors value to be present somewhere.
        assert.ok(JSON.stringify(sent).indexOf('cursor123') !== -1, 'sent payload should include server cursor data');
    });

    // Test when syncSessions returns empty arrays (edge case)
    })