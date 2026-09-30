let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
const path = require('path');

describe('test testpilot_subject.file_0009.CodeIndexSearchService.prototype.searchIndex', function() {
    // Grab the prototype function so we can call it with a fake "this" without needing the real constructor.
    const searchIndexFn = testpilot_subject.file_0009.CodeIndexSearchService.prototype.searchIndex;

    // Keep original console.error to restore later
    let originalConsoleError;
    before(function() {
        originalConsoleError = console.error;
        // Silence console.error during tests to avoid noisy output
        console.error = () => {};
    });
    after(function() {
        console.error = originalConsoleError;
    });

    it('throws if feature is disabled or not configured', async function() {
        const fakeThis = {
            configManager: {
                isFeatureEnabled: false,
                isFeatureConfigured: true, // either false would trigger as well
            },
            // stateManager/embedder/vectorStore should not be used in this path but provide minimal stubs
            stateManager: {
                getCurrentStatus: () => ({ systemStatus: 'Indexed' }),
                setSystemState: () => {}
            },
            embedder: {},
            vectorStore: {}
        };

        try {
            await searchIndexFn.call(fakeThis, 'query', null);
            assert.fail('Expected error was not thrown');
        } catch (err) {
            assert.ok(err instanceof Error);
            assert.strictEqual(err.message, 'Code index feature is disabled or not configured.');
        }
    });

    })