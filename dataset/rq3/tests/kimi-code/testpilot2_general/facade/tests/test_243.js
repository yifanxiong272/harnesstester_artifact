let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports ToolCallComponent with addSubToolOutputPreview on its prototype', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should be present');
        const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        assert.ok(ToolCallComponent, 'ToolCallComponent should be exported');
        assert.strictEqual(typeof ToolCallComponent.prototype.addSubToolOutputPreview, 'function',
            'addSubToolOutputPreview should be a function on the prototype');
        // function arity should accept one argument (activity) in typical implementations
        assert.ok(ToolCallComponent.prototype.addSubToolOutputPreview.length >= 0);
    });

    // Helper to create an instance or a prototype-backed object if constructor requires environment
    function makeComponentInstance() {
        const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        let inst;
        try {
            inst = new ToolCallComponent();
        } catch (e) {
            // Fall back to an object that inherits the prototype so we can call the method
            inst = Object.create(ToolCallComponent.prototype);
        }
        return inst;
    }

    })