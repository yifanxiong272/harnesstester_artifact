let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('module shape: file_0004 and PromptManager exist', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be defined');
        assert.ok(testpilot_subject.file_0004, 'file_0004 should be exported');
        assert.ok(testpilot_subject.file_0004.PromptManager, 'PromptManager should be exported in file_0004');
    });

    })