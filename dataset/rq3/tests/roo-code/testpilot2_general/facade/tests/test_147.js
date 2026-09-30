let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('OutputManager class and outputReasoningMessage method exist', function() {
        assert.ok(testpilot_subject, 'module should be present');
        // Ensure path exists
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace should exist');
        assert.ok(typeof testpilot_subject.file_0002.OutputManager === 'function', 'OutputManager should be a constructor');
        let mgr = new testpilot_subject.file_0002.OutputManager();
        assert.strictEqual(typeof mgr.outputReasoningMessage, 'function', 'outputReasoningMessage should be a function on the instance');
    });

    })