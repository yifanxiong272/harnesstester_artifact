let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const C = testpilot_subject.file_0001.OpenAiCodexOAuthManager;

    it('isAuthenticated -> false when getAccessToken resolves to null', async function() {
        const mgr = Object.create(C.prototype);
        mgr.getAccessToken = async () => null;
        const result = await mgr.isAuthenticated();
        assert.strictEqual(result, false);
    });

    })