let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0002.FsSearchService.prototype.dispose', function() {
  const FsSearchService = testpilot_subject.file_0002.FsSearchService;
  // The base prototype (the "super" prototype) where super.dispose will be found.
  const baseProto = Object.getPrototypeOf(FsSearchService.prototype);
  const originalBaseDispose = baseProto && baseProto.dispose;

  // Restore original after the suite to avoid side-effects.
  after(function() {
    if (baseProto) {
      baseProto.dispose = originalBaseDispose;
    }
  });

  it('calls gitignoreCache.clear and then the base dispose once', function() {
    let clearCalled = 0;
    let baseCalled = 0;

    // Spy on base (super) dispose
    baseProto.dispose = function() {
      baseCalled++;
    };

    // Create an instance without invoking constructor (avoids external setup)
    const instance = Object.create(FsSearchService.prototype);
    instance.gitignoreCache = {
      clear: function() {
        clearCalled++;
      }
    };

    // Call the method under test
    instance.dispose();

    assert.strictEqual(clearCalled, 1, 'gitignoreCache.clear should be called once');
    assert.strictEqual(baseCalled, 1, 'super.dispose (base dispose) should be called once');
  });

  })