let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0003.ToolCallComponent.prototype.getSubagentAgentId', function() {
    const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;

    it('returns existing subagentAgentId without inspecting toolCall/result', function() {
      const obj = Object.create(proto);
      obj.subagentAgentId = 'agent-preexisting';
      // Even if toolCall/result would normally prevent extraction, existing value should be returned
      obj.toolCall = { name: 'NotAgent' };
      obj.result = undefined;
      assert.strictEqual(obj.getSubagentAgentId(), 'agent-preexisting');
    });

        })
})