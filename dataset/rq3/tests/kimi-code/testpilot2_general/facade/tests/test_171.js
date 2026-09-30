let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0003.ToolCallComponent.prototype.getAgentToolDescription', function() {
    it('returns undefined when toolCall.name is not "Agent"', function() {
      const obj = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);
      obj.toolCall = { name: 'NotAgent', args: { description: 'some-desc' } };
      assert.strictEqual(obj.getAgentToolDescription(), undefined);
    });

        })
})