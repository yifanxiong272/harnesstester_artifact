let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.isFailoverAssistantError', function() {
    let origIsFailoverErrorMessage;

    beforeEach(function() {
      // save original so tests don't permanently mutate module
      origIsFailoverErrorMessage = testpilot_subject.file_0001.isFailoverErrorMessage;
    });

    afterEach(function() {
      // restore original implementation
      testpilot_subject.file_0001.isFailoverErrorMessage = origIsFailoverErrorMessage;
    });

    it('returns false when msg is falsy', function() {
      assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(null), false);
      assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(undefined), false);
      assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(0), false);
      assert.strictEqual(testpilot_subject.file_0001.isFailoverAssistantError(''), false);
    });

        })
})