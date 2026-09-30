let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.finishSubToolCall', function() {
        it('should exist and be a function on the prototype', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
            const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
            assert.ok(ToolCallComponent, 'ToolCallComponent should exist');
            assert.strictEqual(typeof ToolCallComponent.prototype.finishSubToolCall, 'function',
                               'finishSubToolCall should be a function on the prototype');
        });

            })
})