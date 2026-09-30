let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  describe('file_0001.generateState', function() {
    it('returns a string of length 32 (16 bytes hex)', function() {
      const s = testpilot_subject.file_0001.generateState();
      assert.strictEqual(typeof s, 'string');
      assert.strictEqual(s.length, 32);
    });

        })
})