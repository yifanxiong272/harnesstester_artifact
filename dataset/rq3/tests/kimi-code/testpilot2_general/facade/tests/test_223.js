let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.formatAgentId', function() {
        const fn = testpilot_subject.file_0003.ToolCallComponent.prototype.formatAgentId;

        it('returns empty string when subagentAgentId is undefined (default)', function() {
            const result = fn.call({});
            assert.strictEqual(result, '');
        });

            })
})