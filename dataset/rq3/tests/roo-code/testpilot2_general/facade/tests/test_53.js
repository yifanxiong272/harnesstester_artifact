let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic availability checks and dynamic tests driven by implementation inspection.
    it('should have OpenAiCodexOAuthManager and cancelAuthorizationFlow defined', function() {
        assert.ok(testpilot_subject, 'testpilot_subject must be present');
        const file0001 = testpilot_subject.file_0001;
        assert.ok(file0001, 'file_0001 must be present on testpilot_subject');
        const Ctor = file0001.OpenAiCodexOAuthManager;
        assert.ok(Ctor, 'OpenAiCodexOAuthManager constructor must be present');
        assert.strictEqual(typeof Ctor.prototype.cancelAuthorizationFlow, 'function',
            'cancelAuthorizationFlow should be a function on the prototype');
    });

    })