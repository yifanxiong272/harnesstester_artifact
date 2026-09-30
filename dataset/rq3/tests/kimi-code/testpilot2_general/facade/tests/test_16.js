let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  // Shortcuts to the target path for readability
  const getTarget = () =>
    testpilot_subject &&
    testpilot_subject.file_0002 &&
    testpilot_subject.file_0002.FsSearchService &&
    testpilot_subject.file_0002.FsSearchService.$di$dependencies &&
    testpilot_subject.file_0002.FsSearchService.$di$dependencies[1];

  let originalId;

  before(function() {
    // Save original id so tests that modify it can restore later
    const target = getTarget();
    if (target) originalId = target.id;
  });

  after(function() {
    // Restore original id (if we successfully saved it)
    const target = getTarget();
    if (target && typeof originalId !== 'undefined') {
      target.id = originalId;
    }
  });

  it('has the expected nested structure and dependency entry', function() {
    const target = getTarget();
    assert.ok(target, 'Expected target path to exist: file_0002.FsSearchService.$di$dependencies[1]');
    assert.ok('id' in target, 'Expected dependency entry to have an "id" property');
  });

  })