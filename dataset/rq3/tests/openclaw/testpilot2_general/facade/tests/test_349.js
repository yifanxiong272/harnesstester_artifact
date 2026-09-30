let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0011.parseBrowserMajorVersion', function() {
    // helper used by tests: compare result to parseInt(raw, 10) semantics
    function assertMatchesParseInt(raw) {
        const res = testpilot_subject.file_0011.parseBrowserMajorVersion(raw);
        const expected = Number.parseInt(raw, 10);
        if (Number.isNaN(expected)) {
            // If parseInt says NaN, require the function to return a numeric NaN as well.
            // (This is a reasonable, non-external-resource requirement for a parsing function.)
            assert.ok(Number.isNaN(res), `expected NaN for input ${JSON.stringify(raw)}, got ${res}`);
        } else {
            assert.strictEqual(res, expected, `expected ${expected} for input ${JSON.stringify(raw)}, got ${res}`);
        }
    }

    it('parses a typical dotted version string', function() {
        assertMatchesParseInt('70.0.3538.77');
    });

    })