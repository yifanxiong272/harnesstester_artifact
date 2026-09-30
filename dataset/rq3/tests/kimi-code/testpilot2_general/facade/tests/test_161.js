let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.markBackgrounded', function() {
        it('should exist on the prototype and be a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
            const proto = testpilot_subject.file_0003.ToolCallComponent &&
                          testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'ToolCallComponent.prototype should exist');
            assert.strictEqual(typeof proto.markBackgrounded, 'function',
                               'markBackgrounded should be a function on the prototype');
        });

            })
})