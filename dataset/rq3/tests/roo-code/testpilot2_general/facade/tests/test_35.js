let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure the class exists before running tests
    it('class OpenAiCodexOAuthManager should be available', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0001, 'file_0001 namespace missing');
        assert.ok(testpilot_subject.file_0001.OpenAiCodexOAuthManager, 'OpenAiCodexOAuthManager missing');
        assert.ok(typeof testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype.getAccountId === 'function');
    });

    })