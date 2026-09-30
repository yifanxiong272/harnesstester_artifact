let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0001.isRateLimitErrorMessage', function() {
    const f = testpilot_subject.file_0001.isRateLimitErrorMessage;

    it('identifies common explicit rate-limit messages', function() {
      assert.strictEqual(f("Rate limit exceeded"), true);
      assert.strictEqual(f("You have exceeded your rate limit"), true);
      assert.strictEqual(f("You have exceeded the rate limit"), true);
      assert.strictEqual(f("Too Many Requests"), true);
      assert.strictEqual(f("429 Too Many Requests"), true);
      assert.strictEqual(f("429: Too Many Requests"), true);
    });

        })
})