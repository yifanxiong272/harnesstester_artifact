let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0001.isTimeoutErrorMessage', function() {
    const fn = testpilot_subject.file_0001.isTimeoutErrorMessage;

    it('returns true for ETIMEDOUT-style messages', function() {
      assert.strictEqual(fn('Error: connect ETIMEDOUT 1.2.3.4:80'), true);
      assert.strictEqual(fn('connect ETIMEDOUT'), true);
    });

        })
})