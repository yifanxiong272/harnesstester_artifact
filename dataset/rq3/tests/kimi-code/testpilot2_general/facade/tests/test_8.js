let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  const targetPath = [
    'file_0002',
    'FsSearchService',
    '$di$dependencies',
  ];

  function resolveId(subject) {
    // Safely traverse the expected path to the id object.
    try {
      const file = subject[targetPath[0]];
      const svc = file && file[targetPath[1]];
      const deps = svc && svc[targetPath[2]];
      const firstDep = Array.isArray(deps) ? deps[0] : undefined;
      return firstDep && firstDep.id;
    } catch (e) {
      return undefined;
    }
  }

  it('should expose the id object with a toString function', function() {
    const id = resolveId(testpilot_subject);
    assert.ok(id, 'expected id to be present');
    assert.strictEqual(typeof id.toString, 'function', 'id.toString should be a function');
  });

  })