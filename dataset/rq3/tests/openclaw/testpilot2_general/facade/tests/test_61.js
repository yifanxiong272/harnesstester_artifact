let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('testpilot_subject.file_0001.isCloudCodeAssistFormatError', function() {
    const subject = testpilot_subject.file_0001;
    let origIsImageDim;
    let origImportFailover;

    beforeEach(function() {
      // save originals if present so we can restore after tests
      origIsImageDim = subject.hasOwnProperty('isImageDimensionErrorMessage')
        ? subject.isImageDimensionErrorMessage
        : undefined;
      origImportFailover = subject.hasOwnProperty('import_failover_matches')
        ? subject.import_failover_matches
        : undefined;
    });

    afterEach(function() {
      // restore originals
      if (origIsImageDim === undefined) {
        delete subject.isImageDimensionErrorMessage;
      } else {
        subject.isImageDimensionErrorMessage = origIsImageDim;
      }

      if (origImportFailover === undefined) {
        delete subject.import_failover_matches;
      } else {
        subject.import_failover_matches = origImportFailover;
      }
    });

    it('returns false when isImageDimensionErrorMessage(raw) is true (even if matcher returns true)', function() {
      subject.isImageDimensionErrorMessage = function(raw) { return true; };
      subject.import_failover_matches = { matchesFormatErrorPattern: function(raw) { return true; } };

      const result = subject.isCloudCodeAssistFormatError('some error text');
      assert.strictEqual(result, false);
    });

        })
})