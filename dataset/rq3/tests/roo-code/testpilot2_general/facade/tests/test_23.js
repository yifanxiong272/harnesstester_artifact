let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('returns early when there is no context (credentials remain unchanged)', async function() {
        // obtain the prototype that contains the method under test
        const proto = testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype;
        // create a plain object and set its prototype to the manager prototype so we can call the method
        const manager = { credentials: { token: 'keep-me' } };
        Object.setPrototypeOf(manager, proto);

        await manager.clearCredentials(); // should simply return without changing credentials
        assert.deepStrictEqual(manager.credentials, { token: 'keep-me' });
    });

    })