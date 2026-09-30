let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0008.renderExecHostLabel', function() {
    it('returns "sandbox" when host is "sandbox"', function() {
      assert.strictEqual(
        testpilot_subject.file_0008.renderExecHostLabel("sandbox"),
        "sandbox"
      );
    });

        })
})