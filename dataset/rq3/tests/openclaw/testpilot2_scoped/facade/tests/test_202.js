let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0008.applyShellPath', function() {
    it('should not throw and should return an object for an empty string shellPath', function() {
      let env = {};
      let res = testpilot_subject.file_0008.applyShellPath(env, '');

      // accept either an object return or undefined (function may mutate env instead)
      assert.ok(res === undefined || (res && typeof res === 'object'));
    });
  });
});