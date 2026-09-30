let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0001.isAuthPermanentErrorMessage', function() {
        let fn = testpilot_subject.file_0001.isAuthPermanentErrorMessage;

        it('should return false for transient or unrelated messages', function() {
            // messages that normally indicate a transient problem or unrelated issue
            assert.strictEqual(fn('Temporary server error, please try again later.'), false);
            assert.strictEqual(fn('Network error - please retry'), false);
            assert.strictEqual(fn('Service unavailable (503)'), false);
        });

            })
})