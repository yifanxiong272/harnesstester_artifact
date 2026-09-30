let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.OpenAiCodexOAuthManager', function() {
        it('should export a constructor (function)', function() {
            // Ensure the export exists and is callable as a constructor
            let OpenAiCodexOAuthManager = testpilot_subject.file_0001.OpenAiCodexOAuthManager;
            assert.ok(OpenAiCodexOAuthManager, 'OpenAiCodexOAuthManager is missing');
            assert.equal(typeof OpenAiCodexOAuthManager, 'function', 'OpenAiCodexOAuthManager should be a function/constructor');
        });

            })
})