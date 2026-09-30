let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0016.resolveAcpClientSpawnEnv', function() {
    it('returns an object copy containing base env keys and does not mutate baseEnv', function() {
      const baseEnv = { TEST_UNIQUE_BASE: '1', OTHER: '2' };
      const options = {};
      const result = testpilot_subject.file_0016.resolveAcpClientSpawnEnv(baseEnv, options);

      assert.strictEqual(typeof result, 'object');
      assert.notStrictEqual(result, baseEnv, 'result should be a new object, not the same reference as baseEnv');
      assert.strictEqual(result.TEST_UNIQUE_BASE, '1');
      assert.strictEqual(result.OTHER, '2');

      // baseEnv must remain unchanged
      assert.strictEqual(baseEnv.TEST_UNIQUE_BASE, '1');
      assert.strictEqual(baseEnv.OTHER, '2');
    });

        })
})