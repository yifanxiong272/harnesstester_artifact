let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.buildContent', function() {
        it('should exist and be a function on the prototype', function() {
            let ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
            assert.ok(ToolCallComponent, 'ToolCallComponent is expected to be exported');
            assert.strictEqual(typeof ToolCallComponent.prototype.buildContent, 'function',
                'buildContent should be a function on the prototype');
        });

            })
})