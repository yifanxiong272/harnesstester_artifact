let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('test testpilot_subject.file_0001.isRawApiErrorPayload', function() {
        // Backup original function so we can restore after tests
        let originalGetFingerprint;
        before(function() {
            originalGetFingerprint = testpilot_subject.file_0001.getApiErrorPayloadFingerprint;
        });

        after(function() {
            // Restore original even if tests modified it
            testpilot_subject.file_0001.getApiErrorPayloadFingerprint = originalGetFingerprint;
        });

        it('returns false when getApiErrorPayloadFingerprint returns null', function() {
            // Stub fingerprint function to return null except for a different sentinel
            testpilot_subject.file_0001.getApiErrorPayloadFingerprint = function(raw) {
                if (raw === 'ONLY_VALID_FOR_OTHER_TEST') return 'fp';
                return null;
            };

            assert.strictEqual(
                testpilot_subject.file_0001.isRawApiErrorPayload('some other input'),
                false,
                'should return false when fingerprint is null'
            );
        });

            })
})