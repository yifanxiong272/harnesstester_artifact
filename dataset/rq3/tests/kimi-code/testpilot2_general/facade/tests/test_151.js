let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.onSubagentStarted', function() {
        it('exists and is a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0003, 'file_0003 should exist on module');
            const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'ToolCallComponent prototype should exist');
            assert.strictEqual(typeof proto.onSubagentStarted, 'function', 'onSubagentStarted should be a function');
        });

            })
})