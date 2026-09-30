let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0004.injectSyntheticToolResults', function() {
    it('should exist and be a function', function() {
      assert.ok(testpilot_subject, 'testpilot_subject module should be present');
      assert.ok(testpilot_subject.file_0004, 'file_0004 should be present on module');
      assert.strictEqual(
        typeof testpilot_subject.file_0004.injectSyntheticToolResults,
        'function',
        'injectSyntheticToolResults should be a function'
      );
    });

        })
})