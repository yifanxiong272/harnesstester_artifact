let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent and buildHeaderChip exist', function() {
        // Basic existence checks. If the module layout changes this will fail fast.
        assert.ok(testpilot_subject, 'testpilot_subject module is not available');
        assert.ok(testpilot_subject.file_0003, 'testpilot_subject.file_0003 is not available');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent is not available');
        assert.strictEqual(typeof testpilot_subject.file_0003.ToolCallComponent.prototype.buildHeaderChip, 'function',
            'buildHeaderChip should be a function on the prototype');
    });

    })