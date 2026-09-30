let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic existence checks and simple behavior tests for FsWatcherService.dispose()
    it('FsWatcherService.prototype.dispose should exist and be a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0001, 'file_0001 namespace should be present');
        const FsWatcherService = testpilot_subject.file_0001.FsWatcherService;
        assert.ok(FsWatcherService, 'FsWatcherService should be exported');
        assert.strictEqual(typeof FsWatcherService.prototype.dispose, 'function', 'dispose should be a function on the prototype');
    });

    })