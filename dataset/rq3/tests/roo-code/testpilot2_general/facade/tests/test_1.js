let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('saveCredentials should throw if manager not initialized', async function() {
        const mgr = new testpilot_subject.file_0001.OpenAiCodexOAuthManager();
        let threw = false;
        try {
            await mgr.saveCredentials({ access_token: "a", refresh_token: "r", expires: Date.now() + 10000 });
        } catch (err) {
            threw = true;
            assert.ok(err instanceof Error, "Expected an Error to be thrown");
            assert.strictEqual(err.message, "OAuth manager not initialized");
        }
        assert.strictEqual(threw, true, "saveCredentials did not throw when context was not initialized");
    });

    })