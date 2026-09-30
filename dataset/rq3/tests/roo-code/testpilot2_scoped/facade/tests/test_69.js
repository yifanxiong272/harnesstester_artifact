let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0008.OpenAICompatibleHandler.prototype.getMaxOutputTokens', function() {
    it('should exist and be a function', function() {
      assert.ok(testpilot_subject, 'testpilot_subject module not found');
      assert.ok(testpilot_subject.file_0008, 'testpilot_subject.file_0008 not found');
      let Handler = testpilot_subject.file_0008.OpenAICompatibleHandler;
      assert.ok(typeof Handler === 'function', 'OpenAICompatibleHandler constructor missing or not a function');
      assert.ok(typeof Handler.prototype.getMaxOutputTokens === 'function', 'getMaxOutputTokens is not a function on the prototype');
    });

        })
})