let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.formatAgentId', function() {
        it('should exist and be a function on the prototype', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0003, 'file_0003 namespace missing');
            const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'ToolCallComponent.prototype missing');
            assert.strictEqual(typeof proto.formatAgentId, 'function', 'formatAgentId should be a function');
        });

            })
})