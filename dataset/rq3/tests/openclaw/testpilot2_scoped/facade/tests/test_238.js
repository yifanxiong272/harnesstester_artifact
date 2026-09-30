let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to recreate the original function source but with controllable imports (stubs)
    function makeFnWithStubs(originalFn) {
        const src = originalFn.toString();
        // Build a function body that creates the import_* variables used in the source,
        // binding them to the stubbed functions we pass in as parameters.
        const wrapperCode =
            'const import_system_events = { enqueueSystemEvent: enqueueSystemEvent };' +
            'const import_heartbeat_wake = { requestHeartbeatNow: requestHeartbeatNow };' +
            'const import_session_key = { scopedHeartbeatWakeOptions: scopedHeartbeatWakeOptions };' +
            'return ' + src + ';';
        // The returned value of new Function(...) is a function which when invoked returns the original function.
        return function(stubs) {
            return new Function(
                'enqueueSystemEvent',
                'requestHeartbeatNow',
                'scopedHeartbeatWakeOptions',
                wrapperCode
            )(stubs.enqueueSystemEvent, stubs.requestHeartbeatNow, stubs.scopedHeartbeatWakeOptions);
        };
    }

    const rebuild = makeFnWithStubs(testpilot_subject.file_0008.emitExecSystemEvent);

    it('does nothing when opts.sessionKey is missing', function() {
        let enqueueCalled = false;
        let hbCalled = false;
        const fn = rebuild({
            enqueueSystemEvent: function() { enqueueCalled = true; },
            requestHeartbeatNow: function() { hbCalled = true; },
            scopedHeartbeatWakeOptions: function() { throw new Error('should not be called'); }
        });

        // Call with opts that do not include sessionKey
        const ret = fn('some-text', {});
        assert.strictEqual(ret, undefined, 'function should return undefined');
        assert.strictEqual(enqueueCalled, false, 'enqueueSystemEvent should not have been called');
        assert.strictEqual(hbCalled, false, 'requestHeartbeatNow should not have been called');
    });

    })