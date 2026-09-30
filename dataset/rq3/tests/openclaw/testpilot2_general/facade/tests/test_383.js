let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0012.extractToolResultId', function() {
    it('returns toolCallId when present and non-empty string', function() {
      const msg = { toolCallId: 'abc123' };
      const res = testpilot_subject.file_0012.extractToolResultId(msg);
      assert.strictEqual(res, 'abc123');
    });

        })
})