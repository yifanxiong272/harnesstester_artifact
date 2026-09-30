let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject FsService dispose()', function() {
  // Helper to obtain the FsService constructor in a safe way
  function getFsServiceCtor() {
    if (!testpilot_subject) {
      throw new Error('testpilot_subject module not found');
    }
    if (!testpilot_subject.file_0004 || !testpilot_subject.file_0004.FsService) {
      throw new Error('testpilot_subject.file_0004.FsService is not exported');
    }
    return testpilot_subject.file_0004.FsService;
  }

  // Helper that tries to create an instance but falls back to a prototype-only object
  function createInstance(FsServiceCtor) {
    try {
      // Prefer the real constructor if it works without required external resources
      return new FsServiceCtor();
    } catch (e) {
      // If constructor requires args or throws, create a plain object that uses the prototype
      return Object.create(FsServiceCtor.prototype);
    }
  }

  it('dispose should exist and be a function on the prototype', function() {
    const FsServiceCtor = getFsServiceCtor();
    assert.strictEqual(typeof FsServiceCtor.prototype.dispose, 'function', 'dispose should be a function on the prototype');
  });

  })