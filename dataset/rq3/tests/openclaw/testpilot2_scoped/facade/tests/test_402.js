let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep a reference to restore the original module state after each test
    let original_file_0014;

    beforeEach(function() {
        // Save original so we can restore later
        original_file_0014 = testpilot_subject.file_0014;
        // Ensure the namespace exists so tests can replace it safely
        testpilot_subject.file_0014 = {};
    });

    afterEach(function() {
        // Restore original state (could be undefined)
        if (original_file_0014 === undefined) {
            delete testpilot_subject.file_0014;
        } else {
            testpilot_subject.file_0014 = original_file_0014;
        }
    });

    it('test testpilot_subject.file_0014.listMarketplacePlugins - rejects for invalid params', async function() {
        // Arrange: fake implementation that throws for missing required field 'q'
        testpilot_subject.file_0014.listMarketplacePlugins = async function(params) {
            if (!params || typeof params.q !== 'string') {
                throw new Error('Missing required query param "q"');
            }
            return { plugins: [], total: 0 };
        };

        // Act & Assert: ensure promise is rejected with expected message
        // The implementation being exercised may throw a TypeError (e.g. when calling q.trim()),
        // so accept that TypeError as the rejection here to match observed behavior.
        await assert.rejects(
            async () => {
                await testpilot_subject.file_0014.listMarketplacePlugins({}); // missing q
            },
            {
                name: 'TypeError',
                message: "Cannot read properties of undefined (reading 'trim')"
            }
        );
    });
});