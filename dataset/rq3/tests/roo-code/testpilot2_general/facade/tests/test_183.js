let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0004 and PromptManager is available', function() {
        // Ensure the expected namespace exists
        assert.ok(testpilot_subject.file_0004, 'file_0004 should be exported');
        assert.ok(testpilot_subject.file_0004.PromptManager, 'PromptManager should be exported');
    });

    })