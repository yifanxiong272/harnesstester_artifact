let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.extractObservedOverflowTokenCount', function() {
    // Save/restore any existing patterns so tests are self-contained and do not
    // rely on the module's original patterns.
    let originalPatterns;
    beforeEach(function() {
      originalPatterns = testpilot_subject.file_0001.OBSERVED_OVERFLOW_TOKEN_PATTERNS;
    });
    afterEach(function() {
      testpilot_subject.file_0001.OBSERVED_OVERFLOW_TOKEN_PATTERNS = originalPatterns;
    });

    it('returns undefined for falsy inputs', function() {
      assert.strictEqual(
        testpilot_subject.file_0001.extractObservedOverflowTokenCount(undefined),
        undefined
      );
      assert.strictEqual(
        testpilot_subject.file_0001.extractObservedOverflowTokenCount(null),
        undefined
      );
      assert.strictEqual(
        testpilot_subject.file_0001.extractObservedOverflowTokenCount(''),
        undefined
      );
    });

        })
})