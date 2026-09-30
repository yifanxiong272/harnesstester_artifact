let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const func = testpilot_subject
        && testpilot_subject.file_0001
        && testpilot_subject.file_0001.extractObservedOverflowTokenCount;

    it('exports extractObservedOverflowTokenCount as a function', function() {
        assert.ok(typeof func === 'function', 'extractObservedOverflowTokenCount should be a function');
    });

    // helper to compute expected value: first integer (with optional leading -) in the string representation
    function expectedFromMessage(msg) {
        if (msg === null || msg === undefined) return null;
        const s = String(msg);
        const m = s.match(/-?\d+/);
        return m ? parseInt(m[0], 10) : null;
    }

    // helper to normalize the function result so we can compare numbers even if implementation returns numeric strings
    function normalizeResult(res) {
        if (res === null || res === undefined) return null;
        if (typeof res === 'number') return res;
        if (typeof res === 'string') {
            const m = res.match(/^-?\d+$/);
            if (m) return parseInt(res, 10);
        }
        // if it's something else (object, boolean...), return as-is
        return res;
    }

    })