let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.sanitizeUserFacingText', function() {
    it('returns the same falsy value when given undefined or null', function() {
      assert.strictEqual(testpilot_subject.file_0001.sanitizeUserFacingText(undefined), undefined);
      assert.strictEqual(testpilot_subject.file_0001.sanitizeUserFacingText(null), null);
    });

        })
})