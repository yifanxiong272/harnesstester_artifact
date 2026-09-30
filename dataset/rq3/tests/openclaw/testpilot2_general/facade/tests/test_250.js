let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to support both sync and Promise-returning implementations
    function runFormat(params) {
        try {
            const res = testpilot_subject.file_0009.formatExecFailureReason(params);
            if (res && typeof res.then === 'function') return res;
            return Promise.resolve(res);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('does not mutate the params object', function() {
        const params = {
            code: 42,
            reason: "initial-reason",
            nested: { a: 1, b: [1,2,3] }
        };
        const copy = JSON.parse(JSON.stringify(params));
        return runFormat(params).then(() => {
            assert.deepStrictEqual(params, copy, 'formatExecFailureReason should not mutate its input object');
        });
    });

    })