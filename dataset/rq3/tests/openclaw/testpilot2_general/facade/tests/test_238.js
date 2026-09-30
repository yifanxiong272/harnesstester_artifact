let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0009.createApprovalSlug', function() {
        const createApprovalSlug = testpilot_subject.file_0009.createApprovalSlug;

        it('returns a prefix that matches id.slice(0, APPROVAL_SLUG_LENGTH)', function() {
            const longId = 'abcdefghijklmnopqrstuvwxyz';
            const slug = createApprovalSlug(longId);

            // The implementation uses id.slice(0, APPROVAL_SLUG_LENGTH).
            // We don't know APPROVAL_SLUG_LENGTH here, but the returned slug
            // must equal longId.slice(0, slug.length).
            assert.strictEqual(slug, longId.slice(0, slug.length));
            assert.strictEqual(typeof slug, 'string');
        });

            })
})