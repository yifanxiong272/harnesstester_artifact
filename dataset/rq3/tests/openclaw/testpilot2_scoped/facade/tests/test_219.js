let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.createApprovalSlug', function() {
        it('returns a non-empty string composed of URL-safe characters for a typical string id', function(done) {
            const id = 'abc123';
            const slug = testpilot_subject.file_0008.createApprovalSlug(id);
            assert.strictEqual(typeof slug, 'string', 'slug should be a string');
            assert.ok(slug.length > 0, 'slug should not be empty');
            // URL-safe slug characters (alphanumeric, dash, underscore)
            assert.ok(/^[A-Za-z0-9_-]+$/.test(slug), 'slug should contain only URL-safe characters');
            done();
        });

            })
})