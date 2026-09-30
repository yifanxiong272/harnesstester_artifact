let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const mod = testpilot_subject && testpilot_subject.file_0001;

    it('module should export file_0001 and isAuthPermanentErrorMessage should be a function', function() {
        assert.ok(mod, 'Expected testpilot_subject.file_0001 to exist');
        assert.strictEqual(typeof mod.isAuthPermanentErrorMessage, 'function',
            'Expected isAuthPermanentErrorMessage to be a function');
    });

    describe('isAuthPermanentErrorMessage behavior', function() {
        // backups for restoring after each test
        let backupMatches;
        let patternsContainer;
        let backupAuthPermanent;

        afterEach(function() {
            // restore matchesErrorPatterns if we swapped it
            if (backupMatches !== undefined && mod) {
                mod.matchesErrorPatterns = backupMatches;
            }
            // restore ERROR_PATTERNS.authPermanent if we modified it
            if (patternsContainer && backupAuthPermanent !== undefined) {
                patternsContainer.ERROR_PATTERNS.authPermanent = backupAuthPermanent;
            }
            backupMatches = undefined;
            patternsContainer = undefined;
            backupAuthPermanent = undefined;
        });

            })
})