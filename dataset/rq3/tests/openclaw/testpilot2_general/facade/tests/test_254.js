let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  describe('file_0009.normalizeExecAsk', function() {
    it('returns normalized values for valid inputs', function() {
      const f = testpilot_subject.file_0009.normalizeExecAsk;
      assert.strictEqual(f('OFF'), 'off');
      assert.strictEqual(f(' off '), 'off');
      assert.strictEqual(f('On-Miss'), 'on-miss');
      assert.strictEqual(f('  always  '), 'always');
      // mixed case / spacing
      assert.strictEqual(f(' oFf  '), 'off');
      assert.strictEqual(f('ON-mIss'), 'on-miss');
    });

        })
})