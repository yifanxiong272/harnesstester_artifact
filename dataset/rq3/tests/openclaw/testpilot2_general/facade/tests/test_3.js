let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.classifyFailoverReason', function() {
        let classify = null;
        before(function() {
            // ensure target function exists
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0001, 'file_0001 should be present on testpilot_subject');
            classify = testpilot_subject.file_0001.classifyFailoverReason;
            assert.ok(typeof classify === 'function', 'classifyFailoverReason should be a function');
        });

        it('should classify authentication-related errors as auth', function() {
            const raw = "Authentication failed: invalid API key provided";
            const result = classify(raw);
            assert.ok(result !== undefined, 'result should be defined');
            const lower = (result + '').toLowerCase();
            // Accept results that indicate authentication (e.g., "auth", "authentication", etc.)
            assert.ok(
                /auth/.test(lower) || /credential/.test(lower) || /access/.test(lower),
                'expected classification to indicate auth but got: ' + result
            );
        });

            })
})