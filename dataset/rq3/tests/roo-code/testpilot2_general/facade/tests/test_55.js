let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let Manager = testpilot_subject &&
                  testpilot_subject.file_0001 &&
                  testpilot_subject.file_0001.OpenAiCodexOAuthManager;

    it('OpenAiCodexOAuthManager constructor and getCredentials exist', function() {
        assert.strictEqual(typeof Manager !== 'undefined', true, 'OpenAiCodexOAuthManager should be defined');
        assert.strictEqual(typeof Manager, 'function', 'OpenAiCodexOAuthManager should be a constructor');
        assert.strictEqual(typeof Manager.prototype.getCredentials, 'function', 'getCredentials should be a function on the prototype');
    });

    })