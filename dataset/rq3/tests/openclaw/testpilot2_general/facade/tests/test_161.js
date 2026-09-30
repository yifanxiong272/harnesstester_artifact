let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

function runRepair(messages, options) {
    try {
        const res = testpilot_subject.file_0003.repairToolCallInputs(messages, options);
        if (res && typeof res.then === 'function') return res;
        return Promise.resolve(res);
    } catch (err) {
        return Promise.reject(err);
    }
}

// Helper: check that every value in 'expected' exists and is deepStrictEqual in 'actual'.
// Allows 'actual' to have extra properties (i.e., repaired output can add fields).
function isDeepSubset(expected, actual) {
    // primitives and functions
    if (expected === null || typeof expected !== 'object') {
        return Object.is(expected, actual);
    }
    if (Array.isArray(expected)) {
        if (!Array.isArray(actual)) return false;
        if (expected.length !== actual.length) return false;
        for (let i = 0; i < expected.length; i++) {
            if (!isDeepSubset(expected[i], actual[i])) return false;
        }
        return true;
    }
    // object
    if (typeof actual !== 'object' || actual === null) return false;
    for (let key of Object.keys(expected)) {
        if (!(key in actual)) return false;
        if (!isDeepSubset(expected[key], actual[key])) return false;
    }
    return true;
}

describe('test testpilot_subject', function() {
    it('file_0003.repairToolCallInputs exists and is a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
        assert.strictEqual(typeof testpilot_subject.file_0003.repairToolCallInputs, 'function', 'repairToolCallInputs should be a function');
    });

    })