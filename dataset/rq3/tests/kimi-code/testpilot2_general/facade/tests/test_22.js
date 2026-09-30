let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
  describe('file_0002.FsSearchService.prototype.dispose', function() {

    it('calls gitignoreCache.clear when gitignoreCache is present', function() {
      const FsSearchService = testpilot_subject.file_0002.FsSearchService;
      // create instance without running the constructor to avoid external side effects
      const inst = Object.create(FsSearchService.prototype);

      let cleared = false;
      inst.gitignoreCache = { clear: function() { cleared = true; } };

      // Patch parent dispose to a safe noop to avoid dependency on parent behavior
      const parentProto = Object.getPrototypeOf(FsSearchService.prototype);
      const originalParentDispose = parentProto.dispose;
      parentProto.dispose = function() {};

      try {
        const ret = inst.dispose();
        assert.strictEqual(cleared, true, 'gitignoreCache.clear should be called');
        assert.strictEqual(ret, undefined, 'dispose should return undefined');
      } finally {
        parentProto.dispose = originalParentDispose;
      }
    });

        })
})