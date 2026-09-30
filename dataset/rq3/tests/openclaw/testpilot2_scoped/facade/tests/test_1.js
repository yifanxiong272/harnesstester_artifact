let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
    it('should identify a CLI/session expired error', function() {
        const raw = 'Error: CLI session expired. Please sign in again.';
        const result = testpilot_subject.file_0001.classifyFailoverReason(raw);
        // expected to map to session_expired
        assert.strictEqual(result, 'session_expired');
    });

    })