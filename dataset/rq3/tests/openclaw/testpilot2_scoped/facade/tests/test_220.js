let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const createApprovalSlug = testpilot_subject.file_0008.createApprovalSlug;

    it('returns a prefix of the input string (long input)', function() {
        // Infer the configured APPROVAL_SLUG_LENGTH by passing a very long string
        const longInput = 'A'.repeat(1000);
        const inferredLength = createApprovalSlug(longInput).length;

        // Prepare a sample input longer than the inferred length
        const sample = 'abcdefghijklmnopqrstuvwxyz';
        const expected = sample.slice(0, inferredLength);
        assert.strictEqual(createApprovalSlug(sample), expected);
        // Also ensure the returned length does not exceed the inferred length
        assert.ok(createApprovalSlug(sample).length <= inferredLength);
    });

    })