let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent.prototype.getSubagentElapsedSeconds exists and is a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        let proto = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent prototype should exist');
        assert.strictEqual(typeof proto.getSubagentElapsedSeconds, 'function', 'getSubagentElapsedSeconds should be a function');
    });

    })