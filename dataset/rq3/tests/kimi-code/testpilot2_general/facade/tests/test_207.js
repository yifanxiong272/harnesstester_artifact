let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.buildProgressBlock', function() {
        it('should expose buildProgressBlock as a function on the prototype', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should be present');
            let proto = testpilot_subject.file_0003.ToolCallComponent &&
                        testpilot_subject.file_0003.ToolCallComponent.prototype;
            assert.ok(proto, 'ToolCallComponent.prototype should exist');
            assert.strictEqual(typeof proto.buildProgressBlock, 'function',
                'buildProgressBlock should be a function');
        });

            })
})