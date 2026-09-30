let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('throws when context is missing', async function() {
        const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
        const mgr = new Manager();

        try {
            await mgr.saveCredentials({ token: 'x' });
            assert.fail('Expected saveCredentials to throw when context is missing');
        } catch (err) {
            assert.strictEqual(err && err.message, 'OAuth manager not initialized');
        }
    });

    })