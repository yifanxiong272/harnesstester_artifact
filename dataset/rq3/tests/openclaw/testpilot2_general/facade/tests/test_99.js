let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  describe('file_0001.isFailoverErrorMessage', function() {
    const fn = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.isFailoverErrorMessage;

    it('should be a function', function() {
      assert.strictEqual(typeof fn, 'function', 'isFailoverErrorMessage should be a function');
    });

        })
})