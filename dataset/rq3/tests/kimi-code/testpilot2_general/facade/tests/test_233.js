let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0003.ToolCallComponent.prototype.formatSingleSubagentStatus', function() {
        const ToolCallComponent = testpilot_subject.file_0003 && testpilot_subject.file_0003.ToolCallComponent;
        it('should exist and be a function', function() {
            assert.ok(ToolCallComponent, 'ToolCallComponent is not present on testpilot_subject.file_0003');
            assert.strictEqual(typeof ToolCallComponent.prototype.formatSingleSubagentStatus, 'function',
                'formatSingleSubagentStatus should be a function on the prototype');
        });

            })
})