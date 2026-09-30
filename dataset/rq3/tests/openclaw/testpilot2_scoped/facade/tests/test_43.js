let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isAuthPermanentErrorMessage', function() {
        it('should be deterministic for the same input (pure function behavior)', function() {
            const samples = [
                'invalid_grant',
                '{"error":"invalid_grant","description":"invalid credentials"}',
                '',
                'Completely different message'
            ];

            samples.forEach((raw) => {
                const a = testpilot_subject.file_0001.isAuthPermanentErrorMessage(raw);
                const b = testpilot_subject.file_0001.isAuthPermanentErrorMessage(raw);
                assert.strictEqual(a, b, `expected deterministic result for input: ${raw}`);
            });
        });

            })
})