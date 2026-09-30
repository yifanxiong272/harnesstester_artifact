let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0008.normalizePathPrepend - handles empty input', function() {
        let entries = [];
        let out = testpilot_subject.file_0008.normalizePathPrepend(entries);
        // Should return an array (empty) and not throw
        assert.ok(Array.isArray(out), 'result should be an array');
        assert.strictEqual(out.length, 0, 'result array should be empty for empty input');
    });

    })