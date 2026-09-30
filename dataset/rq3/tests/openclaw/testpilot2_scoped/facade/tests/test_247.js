let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0008.formatExecFailureReason', function() {
    it('is deterministic: calling it twice with the same input returns identical output', function() {
      const fn = testpilot_subject.file_0008.formatExecFailureReason;
      const input = 'deterministic-token-' + Date.now();
      const first = fn(input);
      const second = fn(input);
      assert.strictEqual(first, second, 'expected identical outputs for repeated calls with same input');
    });

        })
})