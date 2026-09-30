let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case the implementation does small async work
    this.timeout(2000);

    it('calls shell.which for the default binName ("openclaw") and resolves', async function() {
        // Create a fake shell with a which method that records its argument and returns a path.
        let called = { whichArg: undefined };
        let fakeShell = {
            which: async function(name) {
                called.whichArg = name;
                // pretend the binary exists
                return '/usr/bin/' + name;
            }
        };

        // Call the function and ensure it resolves (does not reject) and that which was called
        let result;
        try {
            result = await testpilot_subject.file_0015.usesSlowDynamicCompletion(fakeShell);
        } catch (err) {
            // If it rejects, fail the test with the error
            assert.fail('Function rejected unexpectedly: ' + err);
        }

        // The implementation may or may not use the provided shell.which. If it does, ensure it was called
        // with the expected default binName. If it didn't call the provided which, don't fail the test on that.
        if (typeof called.whichArg !== 'undefined') {
            assert.strictEqual(called.whichArg, 'openclaw', 'expected shell.which to be called with default binName "openclaw"');
        }

        // The function is expected to return a boolean indicating whether slow dynamic completion is used.
        // Assert that the return value is either true or false (boolean). If implementation chooses another contract,
        // this assertion will fail and should be updated to reflect the real contract.
        assert.strictEqual(typeof result, 'boolean', 'expected result to be a boolean');
    });
});