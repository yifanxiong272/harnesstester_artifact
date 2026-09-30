let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Try to require the dependency so we can stub it. If it's not available,
    // some tests that assert delegation will be skipped.
    let import_failover_matches = null;
    try {
        import_failover_matches = require('import_failover_matches');
    } catch (e) {
        import_failover_matches = null;
    }

    // Keep a backup so we can restore the original implementation after tests.
    let backupIsBillingErrorMessage = null;

    afterEach(function() {
        if (import_failover_matches && backupIsBillingErrorMessage !== null) {
            import_failover_matches.isBillingErrorMessage = backupIsBillingErrorMessage;
            backupIsBillingErrorMessage = null;
        }
    });

    it('returns false when msg is falsy', function() {
        assert.strictEqual(testpilot_subject.file_0001.isBillingAssistantError(null), false);
        assert.strictEqual(testpilot_subject.file_0001.isBillingAssistantError(undefined), false);
        assert.strictEqual(testpilot_subject.file_0001.isBillingAssistantError(0), false);
    });

    })