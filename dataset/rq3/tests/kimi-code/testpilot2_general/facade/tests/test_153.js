let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent.prototype.onSubagentCompleted should exist and be a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'expected file_0003 to exist on testpilot_subject');
        let fn = testpilot_subject.file_0003.ToolCallComponent &&
                 testpilot_subject.file_0003.ToolCallComponent.prototype &&
                 testpilot_subject.file_0003.ToolCallComponent.prototype.onSubagentCompleted;
        assert.strictEqual(typeof fn, 'function');
    });

    })