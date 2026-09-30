let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('ToolCallComponent.prototype.getRecentSubToolActivities exists and is a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
        const proto = testpilot_subject.file_0003.ToolCallComponent &&
                      testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype should exist');
        assert.strictEqual(typeof proto.getRecentSubToolActivities, 'function',
            'getRecentSubToolActivities should be a function');
    });

    })