let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0003.ToolCallComponent.prototype.applySubagentReplay - method exists', function(done) {
        let ToolCallComponent = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent;
        assert.ok(ToolCallComponent, 'ToolCallComponent constructor should exist');
        assert.strictEqual(typeof ToolCallComponent.prototype.applySubagentReplay, 'function',
            'applySubagentReplay should be a function on the prototype');
        done();
    });

    })