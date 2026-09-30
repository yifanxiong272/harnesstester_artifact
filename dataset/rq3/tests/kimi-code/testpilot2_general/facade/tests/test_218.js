let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.buildSubagentBlock - existence', function(done) {
        // Verify the module and prototype exist and the method is present
        assert.ok(testpilot_subject, 'testpilot_subject module should be present');
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should be present');
        assert.ok(testpilot_subject.file_0003.ToolCallComponent, 'ToolCallComponent should be present');
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype should be present');
        assert.equal(typeof proto.buildSubagentBlock, 'function', 'buildSubagentBlock should be a function');
        done();
    });

    })