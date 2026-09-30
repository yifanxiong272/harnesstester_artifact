let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.isTransientHttpError', function() {
    const fn = testpilot_subject.file_0001.isTransientHttpError;

    it('returns false for empty or whitespace-only strings', function() {
      assert.strictEqual(fn(''), false);
      assert.strictEqual(fn('   \n\t  '), false);
    });

        })
})