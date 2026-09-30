let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure the PromptManager class exists before running tests
    it('has PromptManager implementation', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0004, 'expected file_0004 namespace');
        assert.ok(typeof testpilot_subject.file_0004.PromptManager === 'function', 'expected PromptManager constructor');
    });

    })