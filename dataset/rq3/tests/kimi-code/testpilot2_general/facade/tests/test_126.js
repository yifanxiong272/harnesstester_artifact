let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent should be exported and have buildDetachHintBlock on its prototype', function() {
        // basic export checks
        assert.ok(testpilot_subject, 'testpilot_subject should be importable');
        assert.ok(testpilot_subject.file_0003, 'testpilot_subject.file_0003 should exist');
        const ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        assert.ok(ToolCallComponent, 'ToolCallComponent should be exported');
        assert.equal(typeof ToolCallComponent.prototype.buildDetachHintBlock, 'function',
            'buildDetachHintBlock should be a function on the prototype');
    });

    })