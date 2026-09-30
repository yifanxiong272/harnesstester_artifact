let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0008.buildExecRuntimeErrorOutcome;

    it('returns the expected shape and copies through fields', function() {
        const err = new Error('boom');
        const params = {
            durationMs: 123,
            aggregated: 'some-aggregated-output',
            error: err
        };

        const out = fn(params);

        // static fields
        assert.strictEqual(out.status, 'failed');
        assert.strictEqual(out.exitCode, null);
        assert.strictEqual(out.exitSignal, null);
        assert.strictEqual(out.timedOut, false);
        assert.strictEqual(out.failureKind, 'runtime-error');

        // passthrough fields
        assert.strictEqual(out.durationMs, 123);
        assert.strictEqual(out.aggregated, params.aggregated);

        // reason should be a string and must contain the stringified error and the aggregated output
        assert.strictEqual(typeof out.reason, 'string');
        assert.ok(out.reason.indexOf(String(err)) !== -1, 'reason should include the error string');
        assert.ok(out.reason.indexOf(params.aggregated) !== -1, 'reason should include aggregated output');
    });

    })