let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0004.PromptManager.prototype.promptForYesNoWithTimeout', function() {
        // Helper to create a PromptManager-like object without calling any real constructor.
        function makePM(stubPromptWithTimeout) {
            const pm = Object.create(testpilot_subject.file_0004.PromptManager.prototype);
            pm.promptWithTimeout = stubPromptWithTimeout;
            return pm;
        }

        it('returns default when timed out and passes "y" default when defaultValue is true', async function() {
            const pm = makePM(async (prompt, timeoutMs, defaultPassed) => {
                // defaultValue true -> should pass "y"
                assert.strictEqual(defaultPassed, "y");
                return { value: "n", timedOut: true, cancelled: false };
            });

            const result = await pm.promptForYesNoWithTimeout("Are you sure?", 100, true);
            assert.strictEqual(result, true);
        });

            })
})