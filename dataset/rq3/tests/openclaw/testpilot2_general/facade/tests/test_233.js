let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0009.buildExecRuntimeErrorOutcome - basic properties and values', function(done) {
        const params = {
            durationMs: 1234,
            aggregated: 'stdout\nstderr',
            error: 'boom'
        };
        const out = testpilot_subject.file_0009.buildExecRuntimeErrorOutcome(params);

        // Static expected properties
        assert.strictEqual(out.status, 'failed', 'status should be "failed"');
        assert.strictEqual(out.exitCode, null, 'exitCode should be null');
        assert.strictEqual(out.exitSignal, null, 'exitSignal should be null');
        assert.strictEqual(out.timedOut, false, 'timedOut should be false');
        assert.strictEqual(out.failureKind, 'runtime-error', 'failureKind should be "runtime-error"');

        // Passed-through values
        assert.strictEqual(out.durationMs, params.durationMs, 'durationMs should be passed through');
        assert.strictEqual(out.aggregated, params.aggregated, 'aggregated should be passed through');

        // Reason should be a string and include the error converted to string
        assert.strictEqual(typeof out.reason, 'string', 'reason should be a string');
        assert.ok(out.reason.indexOf(String(params.error)) !== -1, 'reason should include String(error)');

        done();
    });

    })