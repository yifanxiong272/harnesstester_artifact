let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  // Grab the prototype so we don't have to call a possibly side-effecting constructor.
  const OutputManagerProto = testpilot_subject.file_0002.OutputManager.prototype;

  describe('test testpilot_subject.file_0002.OutputManager.prototype.getCurrentlyStreamingTs', function() {
    let instance;

    beforeEach(function() {
      // Create a simple object that delegates to the real prototype so the method is available.
      instance = Object.create(OutputManagerProto);
    });

    it('returns undefined when currentlyStreamingTs is not set', function() {
      assert.strictEqual(instance.getCurrentlyStreamingTs(), undefined);
    });

        })
})