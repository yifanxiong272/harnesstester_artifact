let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0007.MessageProcessor.prototype.handleStateMessage', function() {
    let MessageProcessor;
    let instance;
    let handleStateMessage;

    before(function() {
      // Locate constructor and method
      MessageProcessor = testpilot_subject && testpilot_subject.file_0007 && testpilot_subject.file_0007.MessageProcessor;
      assert.ok(MessageProcessor, 'MessageProcessor constructor should be present at testpilot_subject.file_0007.MessageProcessor');

      // Try to construct an instance; if construction fails, fall back to prototype method with a plain context
      try {
        instance = new MessageProcessor();
        handleStateMessage = instance.handleStateMessage;
      } catch (e) {
        // If constructor requires args or throws, use prototype method and a plain object as "this"
        instance = {};
        handleStateMessage = MessageProcessor.prototype && MessageProcessor.prototype.handleStateMessage;
      }

      assert.ok(typeof handleStateMessage === 'function', 'handleStateMessage should be a function');
    });

    it('should be a function', function() {
      assert.strictEqual(typeof handleStateMessage, 'function');
    });

        })
})