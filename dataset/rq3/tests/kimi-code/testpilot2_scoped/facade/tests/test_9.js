let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
  it('exports file_0001 and FsWatcherService', function() {
    assert.ok(testpilot_subject, 'module should be exported');
    assert.ok(testpilot_subject.file_0001, 'file_0001 should exist on the export');
    assert.ok(
      testpilot_subject.file_0001.FsWatcherService,
      'FsWatcherService should exist on file_0001'
    );
  });

  })