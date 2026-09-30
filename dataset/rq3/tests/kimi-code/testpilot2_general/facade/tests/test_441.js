let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0009.FsWatcherService', function() {
        // Ensure the module path exists and is a constructor
        assert.ok(testpilot_subject, 'testpilot_subject should be defined');
        assert.ok(testpilot_subject.file_0009, 'testpilot_subject.file_0009 should be defined');
        const FsWatcherService = testpilot_subject.file_0009.FsWatcherService;
        assert.ok(FsWatcherService, 'FsWatcherService should be exported');
        assert.strictEqual(typeof FsWatcherService, 'function', 'FsWatcherService should be a constructor function');
    });

    })