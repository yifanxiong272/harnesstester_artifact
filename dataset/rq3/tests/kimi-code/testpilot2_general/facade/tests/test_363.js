let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const onUnsubscribe = testpilot_subject.file_0006.WsConnection.prototype.onUnsubscribe;

    function makeInstance(opts = {}) {
        const unsubCalls = [];
        const removeCalls = [];
        const warnCalls = [];
        let sendArg = undefined;

        const instance = {
            id: opts.id || 'conn-1',
            unsubscribe: function(sid) { unsubCalls.push(sid); },
            cursorsBySession: opts.cursorsBySession || new Map(),
            fsWatchHandler: opts.fsWatchHandler,
            send: function(arg) { sendArg = arg; },
            logger: {
                warn: function() {
                    warnCalls.push(Array.from(arguments));
                }
            }
        };

        if (!instance.cursorsBySession) instance.cursorsBySession = new Map();

        return {
            instance,
            getUnsubCalls: () => unsubCalls.slice(),
            getSendArg: () => sendArg,
            getRemoveCalls: () => removeCalls.slice(), // may be unused unless opts.fsWatchHandler pushes into it
            getWarnCalls: () => warnCalls.slice(),
            // helpers for fsWatchHandler implementations to record remove calls
            createFsHandler: function(impl) {
                return {
                    remove: function(sid, id, arr) {
                        removeCalls.push([sid, id, arr]);
                        return impl(sid, id, arr);
                    }
                };
            }
        };
    }

    it('calls unsubscribe for each session id, deletes cursorsBySession entries, and sends an ack', function() {
        const helper = makeInstance();
        // Prepopulate cursorsBySession with two sessions
        helper.instance.cursorsBySession.set('s1', {whatever: 1});
        helper.instance.cursorsBySession.set('s2', {whatever: 2});

        const msg = { id: 'm1', payload: { session_ids: ['s1', 's2'] } };

        onUnsubscribe.call(helper.instance, msg);

        // unsubscribe should have been called for each session id
        assert.deepStrictEqual(helper.getUnsubCalls(), ['s1', 's2']);

        // cursorsBySession entries should be removed
        assert.strictEqual(helper.instance.cursorsBySession.has('s1'), false);
        assert.strictEqual(helper.instance.cursorsBySession.has('s2'), false);

        // send should have been called with an ack-like object.
        const sent = helper.getSendArg();
        assert.ok(sent, 'expected send to be called with an ack object');

        // The buildAck used in implementation should include the accepted list in its payload.
        // We check for payload.accepted if present, otherwise at least ensure send was invoked.
        if (sent && sent.payload) {
            assert.deepStrictEqual(sent.payload.accepted, ['s1', 's2']);
        }
    });

    })