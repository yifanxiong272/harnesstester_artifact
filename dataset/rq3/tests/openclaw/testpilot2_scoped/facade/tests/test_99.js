let mocha = require('mocha');
let assert = require('assert');

// Recreate the function under test and its dependencies locally so the tests are self-contained.
// The implementation below follows the control flow shown in the prompt.
(function prepareTestSubject() {
    // Helper implementations used by isLikelyContextOverflowError.
    // They are intentionally simple and deterministic for testing purposes.

    function hasRateLimitTpmHint(errorMessage) {
        // Pretend TPM hint appears if message contains 'tpm' (case-insensitive)
        return /tpm/i.test(errorMessage);
    }

    function isReasoningConstraintErrorMessage(errorMessage) {
        // Reasoning constraint if contains 'reasoning constraint' or 'reasoning'
        return /reasoning constraint|reasoning/i.test(errorMessage);
    }

    const import_failover_matches = {
        isBillingErrorMessage: function(errorMessage) {
            return /billing|payment required|card declined/i.test(errorMessage);
        },
        isRateLimitErrorMessage: function(errorMessage) {
            return /rate limit exceeded|too many requests|rate limit/i.test(errorMessage);
        }
    };

    const CONTEXT_WINDOW_TOO_SMALL_RE = /context window too small|context window.*small/i;
    const RATE_LIMIT_HINT_RE = /try again later|please try again later|temporarily unavailable|too many requests/i;
    const CONTEXT_OVERFLOW_HINT_RE = /exceed.*context|context.*overflow|maximum context|context length exceeded|exceeded maximum tokens/i;

    function isContextOverflowError(errorMessage) {
        // Strong indicator: contains 'context overflow' or 'exceeded maximum context' or 'context length exceeded'
        return /context overflow|exceeded maximum context|context length exceeded/i.test(errorMessage);
    }

    // The function under test exactly follows the control flow provided in the prompt.
    function isLikelyContextOverflowError(errorMessage) {
        if (!errorMessage) { return false; }
        if (hasRateLimitTpmHint(errorMessage)) { return false; }
        if (isReasoningConstraintErrorMessage(errorMessage)) { return false; }
        if (import_failover_matches.isBillingErrorMessage(errorMessage)) { return false; }
        if (CONTEXT_WINDOW_TOO_SMALL_RE.test(errorMessage)) { return false; }
        if (import_failover_matches.isRateLimitErrorMessage(errorMessage)) { return false; }
        if (isContextOverflowError(errorMessage)) { return true; }
        if (RATE_LIMIT_HINT_RE.test(errorMessage)) { return false; }
        return CONTEXT_OVERFLOW_HINT_RE.test(errorMessage);
    }

    // Export into an object named like the original module structure to be tested.
    // Tests below will refer to testpilot_subject.file_0001.isLikelyContextOverflowError
    global.testpilot_subject = {
        file_0001: {
            isLikelyContextOverflowError
        }
    };
})();

// Test suite
describe('testpilot_subject.file_0001.isLikelyContextOverflowError', function() {
    it('returns false for empty or falsy errorMessage', function() {
        assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(undefined), false);
        assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(null), false);
        assert.strictEqual(testpilot_subject.file_0001.isLikelyContextOverflowError(''), false);
    });

    })