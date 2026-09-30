let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent.prototype.buildSingleSubagentHeader exists and is a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0003, 'file_0003 should be present on module');
        const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype should exist');
        assert.strictEqual(typeof proto.buildSingleSubagentHeader, 'function', 'buildSingleSubagentHeader should be a function');
    });

    })