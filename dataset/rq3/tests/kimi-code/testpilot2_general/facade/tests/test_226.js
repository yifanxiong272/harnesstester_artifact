let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0003.ToolCallComponent.prototype.isSingleSubagentView', function() {
    const proto = testpilot_subject &&
                  testpilot_subject.file_0003 &&
                  testpilot_subject.file_0003.ToolCallComponent &&
                  testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('should exist and be a function', function() {
        assert.ok(proto, 'ToolCallComponent.prototype is not present on testpilot_subject.file_0003');
        assert.strictEqual(typeof proto.isSingleSubagentView, 'function', 'isSingleSubagentView should be a function');
    });

    })