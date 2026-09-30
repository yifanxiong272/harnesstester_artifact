let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const f = testpilot_subject &&
              testpilot_subject.file_0008 &&
              testpilot_subject.file_0008.buildExecExitOutcome;

    it('buildExecExitOutcome should exist and be a function', function() {
        assert.ok(f, 'buildExecExitOutcome is not present at testpilot_subject.file_0008.buildExecExitOutcome');
        assert.strictEqual(typeof f, 'function', 'buildExecExitOutcome is not a function');
    });

    // Helper to call f and support either sync return or Promise return
    function callBuild(params) {
        try {
            const out = f(params);
            if (out && typeof out.then === 'function') {
                return out;
            }
            return Promise.resolve(out);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    })