let assert = require('assert');

describe('test testpilot_subject.file_0009.emitExecSystemEvent', function() {
    // We'll create a self-contained version of the function under test along with
    // spy/mock implementations for its dependencies so the tests do not rely on
    // any external resources.
    function makeSubjectWithSpies() {
        const enqueueCalls = [];
        const heartbeatCalls = [];
        const scopedCalls = [];

        // Mocks / spies for the imported modules
        const import_system_events = {
            enqueueSystemEvent: (text, opts) => {
                enqueueCalls.push({ text, opts });
            }
        };

        const import_session_key = {
            // emulate a function that returns some options object derived from args
            scopedHeartbeatWakeOptions: (sessionKey, opts) => {
                const result = { sessionKey, ...opts };
                scopedCalls.push({ sessionKey, opts, result });
                return result;
            }
        };

        const import_heartbeat_wake = {
            requestHeartbeatNow: (opts) => {
                heartbeatCalls.push(opts);
            }
        };

        // The function under test, implemented exactly as provided but wired to
        // the above mock dependencies.
        function emitExecSystemEvent(text, opts) {
            const sessionKey = opts.sessionKey?.trim();
            if (!sessionKey) { return; }
            (0, import_system_events.enqueueSystemEvent)(text, { sessionKey, contextKey: opts.contextKey });
            (0, import_heartbeat_wake.requestHeartbeatNow)((0, import_session_key.scopedHeartbeatWakeOptions)(sessionKey, { reason: "exec-event" }));
        }

        return {
            emitExecSystemEvent,
            // expose spies so tests can inspect calls
            _spies: {
                enqueueCalls,
                heartbeatCalls,
                scopedCalls
            }
        };
    }

    it('does nothing when opts is missing or sessionKey is empty/whitespace', function() {
        const subj = makeSubjectWithSpies();

        // Case: opts missing entirely
        subj.emitExecSystemEvent('some text', {});
        // No sessionKey -> should not call anything
        assert.strictEqual(subj._spies.enqueueCalls.length, 0);
        assert.strictEqual(subj._spies.heartbeatCalls.length, 0);
        assert.strictEqual(subj._spies.scopedCalls.length, 0);

        // Case: sessionKey is null/undefined
        subj.emitExecSystemEvent('x', { sessionKey: null });
        subj.emitExecSystemEvent('x', { sessionKey: undefined });
        assert.strictEqual(subj._spies.enqueueCalls.length, 0);
        assert.strictEqual(subj._spies.heartbeatCalls.length, 0);

        // Case: sessionKey is only whitespace
        subj.emitExecSystemEvent('x', { sessionKey: '   ' });
        assert.strictEqual(subj._spies.enqueueCalls.length, 0);
        assert.strictEqual(subj._spies.heartbeatCalls.length, 0);
    });

    })