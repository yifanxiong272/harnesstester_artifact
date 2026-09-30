let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0017.appendBootstrapPromptWarning', function() {
    const fn = testpilot_subject && testpilot_subject.file_0017 && testpilot_subject.file_0017.appendBootstrapPromptWarning;

    it('should export a function', function() {
        assert.strictEqual(typeof fn, 'function', 'appendBootstrapPromptWarning should be a function');
    });

    })