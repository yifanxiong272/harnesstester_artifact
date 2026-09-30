let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0008.applyShellPath', function() {
    it('should set PATH to the provided shellPath when env has no PATH', function() {
      let env = {};
      let shellPath = '/usr/local/bin:/usr/bin';
      let res = testpilot_subject.file_0008.applyShellPath(env, shellPath);

      // allow applyShellPath to either return an object or mutate env in-place
      assert.ok((res && typeof res === 'object') || env.PATH === shellPath);
      // ensure PATH was set (either on the returned object or on the original env)
      assert.strictEqual(res ? res.PATH : env.PATH, shellPath);
    });

        })
})