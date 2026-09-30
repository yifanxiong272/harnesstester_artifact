let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.getAccessToken', function() {
    // Helper to create an instance without running constructor
    function makeManager() {
        const mgr = Object.create(testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype);
        mgr.log = function() {};        // noop logger
        mgr.logError = function() {};   // noop error logger
        mgr.refreshPromise = null;
        // provide defaults so tests only override what they need
        mgr.loadCredentials = async function() {};
        mgr.saveCredentials = async function() {};
        mgr.clearCredentials = async function() {};
        return mgr;
    }

    it('returns null when no credentials after loadCredentials', async function() {
        const mgr = makeManager();
        let loadCalled = false;
        // loadCredentials doesn't set credentials -> should result in null
        mgr.loadCredentials = async function() { loadCalled = true; /* no creds set */ };

        // Ensure isTokenExpired not required here, but don't touch global state
        const token = await mgr.getAccessToken();
        assert.strictEqual(token, null);
        assert.strictEqual(loadCalled, true);
    });

    })