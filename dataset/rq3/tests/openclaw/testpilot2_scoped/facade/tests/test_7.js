let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.extractLeadingHttpStatus', function() {
    const fn = testpilot_subject.file_0001.extractLeadingHttpStatus;

    it('returns null when there is no leading HTTP status', function() {
      assert.strictEqual(fn(''), null);
      assert.strictEqual(fn('No status here'), null);
      // If the input has an HTTP version but no numeric status it should not match
      assert.strictEqual(fn('HTTP/1.1 OK'), null);
    });

        })
})