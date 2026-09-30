let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to safely convert result to a string for inspection
    function stringifySafe(x) {
        try {
            // JSON.stringify(undefined) -> undefined, so convert that to empty string
            const s = JSON.stringify(x);
            return typeof s === 'string' ? s : String(s);
        } catch (e) {
            // fallback for non-serializable values
            try { return String(x); } catch (e2) { return ''; }
        }
    }

    it('has parseImageSizeError exported and is a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0001, 'file_0001 should be present on module');
        assert.strictEqual(typeof testpilot_subject.file_0001.parseImageSizeError, 'function',
            'parseImageSizeError should be a function');
    });

    })