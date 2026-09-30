let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0017.formatBootstrapTruncationWarningLines', function() {
    it('returns empty array when analysis.hasTruncation is false', function() {
      const params = { analysis: { hasTruncation: false } };
      const res = testpilot_subject.file_0017.formatBootstrapTruncationWarningLines(params);
      assert.deepStrictEqual(res, []);
    });

        })
})