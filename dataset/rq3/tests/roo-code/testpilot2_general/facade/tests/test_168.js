let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const section = testpilot_subject && testpilot_subject.file_0004;
    const PM = section && section.PromptManager;
    const isActiveFn = PM && PM.prototype && PM.prototype.isActive;

    it('test testpilot_subject.file_0004.PromptManager.prototype.isActive - exists and is a function', function() {
        assert.ok(section, 'file_0004 section is not present on testpilot_subject');
        assert.ok(PM, 'PromptManager is not present on file_0004');
        assert.strictEqual(typeof isActiveFn, 'function', 'isActive should be a function on PromptManager.prototype');
    });

    })