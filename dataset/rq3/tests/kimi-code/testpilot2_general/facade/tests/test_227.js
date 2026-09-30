let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('returns true when toolCall.name === "Agent" and hasSubagentState() returns true', function() {
        const obj = Object.create(proto);
        obj.toolCall = { name: 'Agent' };
        obj.hasSubagentState = () => true;

        assert.strictEqual(obj.isSingleSubagentView(), true);
    });

    })