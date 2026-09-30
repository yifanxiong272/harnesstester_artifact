let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.loadCredentials', function() {
    it('returns null when context is falsy', async function() {
        // Create an object whose prototype is the class prototype so we can call the method
        const mgr = Object.create(testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype);
        // do not set context -> should return null immediately
        const result = await mgr.loadCredentials();
        assert.strictEqual(result, null);
    });

    })