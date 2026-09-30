let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Get the prototype method under test.
    const ToolCallComponent = testpilot_subject && testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent;
    if (!ToolCallComponent) {
        // If the module shape is unexpected, fail fast so tests don't silently pass.
        throw new Error('testpilot_subject.file_0003.ToolCallComponent is not available');
    }

    it('returns true when name is "Edit", result is undefined, and streamingArguments is present', function() {
        // Create an object that inherits the method from the real prototype.
        const obj = Object.create(ToolCallComponent.prototype);
        obj.toolCall = { name: 'Edit', streamingArguments: { some: 'arg' } };
        // result is intentionally left undefined
        assert.strictEqual(obj.isStreamingEditPreview(), true);
    });

    })