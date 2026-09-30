let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject - FsWatcherService.$di$dependencies[1].id.toString', function() {
  // Resolve the target under test in a safe way and provide helpful error messages.
  function getTarget() {
    if (!testpilot_subject || typeof testpilot_subject !== 'object') {
      throw new Error('testpilot_subject module did not export an object');
    }
    const file0001 = testpilot_subject.file_0001;
    if (!file0001) throw new Error('missing file_0001 export on testpilot_subject');
    const FsWatcherService = file0001.FsWatcherService;
    if (!FsWatcherService) throw new Error('missing FsWatcherService on file_0001');
    const diDeps = FsWatcherService['$di$dependencies'];
    if (!Array.isArray(diDeps)) throw new Error('missing or invalid $di$dependencies on FsWatcherService');
    if (diDeps.length <= 1) throw new Error('$di$dependencies has fewer than 2 entries');
    const dep = diDeps[1];
    if (!dep || typeof dep !== 'object') throw new Error('dependency at index 1 is missing or not an object');
    const id = dep.id;
    if (id === undefined) throw new Error('dependency[1].id is missing');
    return id;
  }

  it('exports the expected path and toString is a function', function() {
    const id = getTarget();
    assert.strictEqual(typeof id.toString, 'function', 'id.toString should be a function');
  });

  })