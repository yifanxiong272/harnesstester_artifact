let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const ToolCallComponent = testpilot_subject &&
                              testpilot_subject.file_0003 &&
                              testpilot_subject.file_0003.ToolCallComponent;

    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.buildPlanPreview - exists', function() {
        // The method should exist on the prototype and be a function
        assert.ok(ToolCallComponent, 'ToolCallComponent class is present');
        assert.ok(ToolCallComponent.prototype, 'ToolCallComponent.prototype is present');
        const fn = ToolCallComponent.prototype.buildPlanPreview;
        assert.strictEqual(typeof fn, 'function', 'buildPlanPreview should be a function');
    });

    })