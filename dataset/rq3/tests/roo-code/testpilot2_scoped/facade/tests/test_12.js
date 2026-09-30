let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.cleanupAfterTruncation', function() {
    it('returns empty array for empty input', function() {
        const msgs = [];
        const out = testpilot_subject.file_0004.cleanupAfterTruncation(msgs);
        assert.deepStrictEqual(out, []);
    });

    })