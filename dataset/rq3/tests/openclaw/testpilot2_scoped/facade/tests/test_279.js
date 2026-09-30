let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports extractToolCallsFromAssistant as a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.strictEqual(typeof testpilot_subject.file_0009.extractToolCallsFromAssistant, 'function',
            'extractToolCallsFromAssistant should be a function');
    });

    })