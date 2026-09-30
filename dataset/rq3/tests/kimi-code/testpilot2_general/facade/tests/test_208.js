let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a minimal ToolCallComponent-like instance that uses the real prototype
    function makeInstance() {
        // If the module doesn't expose the nested path, fail loudly so tests are explicit.
        assert.ok(testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent not found on testpilot_subject.file_0003');
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        // Create object with the prototype so buildProgressBlock is available
        const obj = Object.create(proto);
        // Provide default properties the method expects
        obj.progressLines = [];
        // result undefined by default
        // capture addChild calls
        obj._added = [];
        obj.addChild = function(child) { this._added.push(child); };
        return obj;
    }

    it('does nothing when progressLines is empty', function() {
        const inst = makeInstance();
        // Ensure no lines
        inst.progressLines = [];
        inst.result = undefined;
        // Call method
        inst.buildProgressBlock();
        // Should not have added children
        assert.strictEqual(inst._added.length, 0, 'Expected no children to be added when progressLines is empty');
    });

    })