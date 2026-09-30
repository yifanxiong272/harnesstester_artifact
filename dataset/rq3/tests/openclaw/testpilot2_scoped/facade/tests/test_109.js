let mocha = require('mocha');
let assert = require('assert');

// Load modules under test
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isRateLimitAssistantError', function() {
    // Try to get the imported matcher so we can stub it deterministically.
    // If the module doesn't exist in this environment, tests that rely on stubbing will be skipped.
    let matchesModule;
    let originalMatcher;
    try {
        matchesModule = require('import_failover_matches');
        originalMatcher = matchesModule.isRateLimitErrorMessage;
    } catch (e) {
        matchesModule = null;
    }

    afterEach(function() {
        // Restore original matcher if we replaced it
        if (matchesModule && originalMatcher) {
            matchesModule.isRateLimitErrorMessage = originalMatcher;
        }
    });

    it('returns false for falsy msg', function() {
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(null), false);
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(undefined), false);
        assert.strictEqual(testpilot_subject.file_0001.isRateLimitAssistantError(false), false);
    });

    })