let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  // Helper to safely access the nested id and its toString
  function getIdToString() {
    assert.ok(testpilot_subject, 'module testpilot_subject should be present');
    assert.ok(testpilot_subject.file_0001, 'file_0001 should be present');
    assert.ok(testpilot_subject.file_0001.FsWatcherService, 'FsWatcherService should be present');
    assert.ok(Array.isArray(testpilot_subject.file_0001.FsWatcherService.$di$dependencies),
      '$di$dependencies should be an array');
    assert.ok(testpilot_subject.file_0001.FsWatcherService.$di$dependencies.length > 0,
      '$di$dependencies should not be empty');

    const dep0 = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0];
    assert.ok(dep0 && typeof dep0 === 'object', 'dependency item should be an object');
    const id = dep0.id;
    assert.ok(id, 'id should be present on the dependency');
    assert.ok(typeof id.toString === 'function', 'id.toString should be a function');
    return id;
  }

  it('id.toString exists and is callable', function() {
    const id = getIdToString();
    // calling should not throw
    const result = id.toString();
    assert.strictEqual(typeof result, 'string', 'toString() should return a string');
  });

  })