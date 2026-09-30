let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.isRateLimitErrorMessage', function() {
        it('returns true for common rate-limit error messages', function() {
            const fn = testpilot_subject.file_0001.isRateLimitErrorMessage;
            assert.strictEqual(fn('Rate limit exceeded'), true, 'expected "Rate limit exceeded" to be recognized');
            assert.strictEqual(fn('You have exceeded the rate limit.'), true, 'expected "You have exceeded the rate limit." to be recognized');
            assert.strictEqual(fn('Too many requests'), true, 'expected "Too many requests" to be recognized');
            assert.strictEqual(fn('ERROR: Rate limit exceeded for user 123'), true, 'expected text containing rate limit to be recognized');
            // Case-insensitivity or surrounding text should still match if patterns allow it
            assert.strictEqual(fn('rate limit exceeded'), true, 'expected lowercase "rate limit exceeded" to be recognized');
            assert.strictEqual(fn('Server response: Too Many Requests (429)'), true, 'expected message with extra context to be recognized');
        });

            })
})