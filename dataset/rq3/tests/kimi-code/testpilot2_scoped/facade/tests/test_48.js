let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsWatcherService = testpilot_subject &&
        testpilot_subject.file_0001 &&
        testpilot_subject.file_0001.FsWatcherService;

    it('FsWatcherService.prototype.watchedPaths should exist and be a function', function() {
        assert.ok(FsWatcherService, 'FsWatcherService constructor is missing at testpilot_subject.file_0001.FsWatcherService');
        assert.strictEqual(typeof FsWatcherService.prototype.watchedPaths, 'function',
            'watchedPaths should be a function on the prototype');
    });

    })