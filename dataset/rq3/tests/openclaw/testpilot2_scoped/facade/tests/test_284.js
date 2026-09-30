let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const extract = testpilot_subject.file_0009.extractToolResultId;

    it('returns toolCallId when present and non-empty string', function() {
        const msg = { toolCallId: 'call-123' };
        assert.strictEqual(extract(msg), 'call-123');
    });

    })