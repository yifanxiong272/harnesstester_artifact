let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // convenience references to the module under test
    const mod = testpilot_subject.file_0001;
    const Manager = mod.OpenAiCodexOAuthManager;

    // Reset any global stubs between tests if present on the module
    beforeEach(function() {
        // remove any previously set stubs on module-level helpers we will override in tests
        if (mod._original_refreshAccessToken) {
            mod.refreshAccessToken = mod._original_refreshAccessToken;
            delete mod._original_refreshAccessToken;
        }
        if (mod._original_OpenAiCodexOAuthTokenError) {
            mod.OpenAiCodexOAuthTokenError = mod._original_OpenAiCodexOAuthTokenError;
            delete mod._original_OpenAiCodexOAuthTokenError;
        }
    });

    afterEach(function() {
        // same cleanup as beforeEach to be safe
        if (mod._original_refreshAccessToken) {
            mod.refreshAccessToken = mod._original_refreshAccessToken;
            delete mod._original_refreshAccessToken;
        }
        if (mod._original_OpenAiCodexOAuthTokenError) {
            mod.OpenAiCodexOAuthTokenError = mod._original_OpenAiCodexOAuthTokenError;
            delete mod._original_OpenAiCodexOAuthTokenError;
        }
    });

    it('returns null when there are no credentials (loadCredentials yields nothing)', async function() {
        const inst = new Manager();

        // stub loadCredentials to be called but leave credentials as null
        let loadCalled = false;
        inst.loadCredentials = async function() {
            loadCalled = true;
            // do not set this.credentials -> simulate missing credentials after load
            return;
        };

        // ensure credentials initially falsy
        inst.credentials = null;

        const result = await inst.forceRefreshAccessToken();
        assert.strictEqual(loadCalled, true, 'loadCredentials should have been invoked');
        assert.strictEqual(result, null, 'Expected null when credentials are not available');
    });

    })