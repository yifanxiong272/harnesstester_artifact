let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  // Helper to safely retrieve the dependency entry at index 0
  function getDependencyEntry() {
    // Use bracket notation to avoid any issues with unusual identifier names
    const root = testpilot_subject;
    if (!root) return undefined;
    const file0002 = root['file_0002'];
    if (!file0002) return undefined;
    const svc = file0002['FsSearchService'];
    if (!svc) return undefined;
    const deps = svc['$di$dependencies'];
    if (!Array.isArray(deps)) return undefined;
    return deps[0];
  }

  it('should expose a dependency entry at file_0002.FsSearchService.$di$dependencies[0]', function() {
    const entry = getDependencyEntry();
    assert.ok(entry, 'expected dependency entry to exist');
    // Basic shape checks
    assert.strictEqual(typeof entry, 'object', 'entry should be an object');
    assert.ok('id' in entry, 'entry should have an id property');
  });

  })