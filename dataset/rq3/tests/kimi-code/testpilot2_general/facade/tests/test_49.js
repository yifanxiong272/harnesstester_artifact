let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.invalidate', function() {
        let ToolCallComponent;

        before(function() {
            // make sure the path exists so tests fail early and clearly if module shape is different
            assert.ok(testpilot_subject, 'testpilot_subject module is required');
            assert.ok(testpilot_subject.file_0003, 'testpilot_subject.file_0003 is present');
            ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
            assert.ok(ToolCallComponent, 'ToolCallComponent exists');
        });

        it('should be a function on the prototype', function() {
            assert.strictEqual(typeof ToolCallComponent.prototype.invalidate, 'function',
                'invalidate should be a function on the prototype');
        });

            })
})