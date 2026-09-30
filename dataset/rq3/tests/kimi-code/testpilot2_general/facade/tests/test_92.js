let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ToolCallComponent = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent;

    it('ToolCallComponent.prototype.getSubagentSnapshot should exist and be a function', function() {
        assert.ok(ToolCallComponent, 'ToolCallComponent constructor is expected to exist');
        assert.strictEqual(typeof ToolCallComponent.prototype.getSubagentSnapshot, 'function',
            'getSubagentSnapshot should be a function on the prototype');
    });

    })