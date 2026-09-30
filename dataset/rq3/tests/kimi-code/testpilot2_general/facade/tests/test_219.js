let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('buildSubagentBlock: does nothing when there is no subagent info', function() {
        // Create object with the prototype method but without running constructor
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        const obj = Object.create(proto);

        // Ensure all the checked properties are "empty" to trigger the early return
        obj.subagentAgentId = undefined;
        obj.ongoingSubCalls = new Map();
        obj.finishedSubCalls = [];
        obj.subagentText = "";
        obj.subagentPhase = undefined;
        obj.backgroundTaskTerminalPhase = undefined;

        // Spy addChild to detect any calls
        let addChildCalls = 0;
        obj.addChild = function() { addChildCalls++; };

        // Call method
        proto.buildSubagentBlock.call(obj);

        // Expect no children added
        assert.strictEqual(addChildCalls, 0, 'Expected no addChild calls when there is no subagent info');
    });

    })