let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should handle an empty messages array without error', function() {
        let messages = [];
        let sanitized = testpilot_subject.file_0012.sanitizeToolCallIdsForCloudCodeAssist(messages, "strict");
        assert(Array.isArray(sanitized), 'result should be an array');
        assert.strictEqual(sanitized.length, 0, 'result should be empty for empty input');
    });

    })