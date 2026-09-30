let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0009.buildExecExitOutcome', function() {
    it('returns completed for normal exit with code 0', function() {
        const params = {
            exit: {
                reason: 'exit',
                exitCode: 0,
                exitSignal: null,
                timedOut: false
            },
            durationMs: 123,
            aggregated: 'standard output',
            timeoutSec: 10
        };

        const result = testpilot_subject.file_0009.buildExecExitOutcome(params);

        assert.strictEqual(result.status, 'completed');
        assert.strictEqual(result.exitCode, 0);
        assert.strictEqual(result.exitSignal, null);
        assert.strictEqual(result.durationMs, 123);
        assert.strictEqual(result.timedOut, false);
        // No extra exit message for code 0
        assert.strictEqual(result.aggregated, 'standard output');
    });

    })