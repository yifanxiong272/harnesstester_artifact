let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.rebuildContent', function() {
    it('should exist and be a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent should exist');
        assert.strictEqual(typeof testpilot_subject.file_0003.ToolCallComponent.prototype.rebuildContent, 'function');
    });

    })