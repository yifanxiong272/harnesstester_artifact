let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0008.applyShellPath', function() {
    it('should leave PATH unchanged when shellPath is null or undefined', function() {
      // use separate env objects and assert on the env itself, because
      // applyShellPath may modify in-place and/or return undefined.
      let env1 = { PATH: '/original' };
      testpilot_subject.file_0008.applyShellPath(env1, undefined);
      assert.strictEqual(env1.PATH, '/original');

      let env2 = { PATH: '/original' };
      testpilot_subject.file_0008.applyShellPath(env2, null);
      assert.strictEqual(env2.PATH, '/original');
    });

  })
})