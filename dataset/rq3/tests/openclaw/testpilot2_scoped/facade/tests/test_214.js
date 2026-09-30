let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.buildExecExitOutcome', function() {
    const fn = testpilot_subject.file_0008.buildExecExitOutcome;

    it('returns completed for zero exit code and preserves aggregated', function() {
        const params = {
            exit: {
                exitCode: 0,
                exitSignal: null,
                reason: "exit",
                timedOut: false
            },
            durationMs: 123,
            aggregated: "some output",
            timeoutSec: 5
        };
        const out = fn(params);
        assert.strictEqual(out.status, "completed");
        assert.strictEqual(out.exitCode, 0);
        assert.strictEqual(out.exitSignal, params.exit.exitSignal);
        assert.strictEqual(out.durationMs, params.durationMs);
        assert.strictEqual(out.aggregated, params.aggregated); // no appended message for code 0
        assert.strictEqual(out.timedOut, false);
    });

    })