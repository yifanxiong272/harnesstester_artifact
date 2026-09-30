let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const Manager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
    const proto = Manager && Manager.prototype;

    it('has getEmail on the prototype and it is async', function() {
        assert.ok(proto, 'OpenAiCodexOAuthManager.prototype should exist');
        assert.strictEqual(typeof proto.getEmail, 'function', 'getEmail should be a function');
        // Async functions have constructor name "AsyncFunction"
        const ctorName = proto.getEmail.constructor && proto.getEmail.constructor.name;
        assert.strictEqual(ctorName, 'AsyncFunction', 'getEmail should be an async function');
    });

    })