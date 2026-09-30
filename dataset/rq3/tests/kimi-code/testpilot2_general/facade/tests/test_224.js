let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('hasSubagentState should exist and be a function', function(done) {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent should exist');
        let proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.strictEqual(typeof proto.hasSubagentState, 'function', 'hasSubagentState should be a function');
        done();
    });

    })