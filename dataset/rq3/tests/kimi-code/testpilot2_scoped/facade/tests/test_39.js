let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.FsWatcherService.prototype.countForConnection', function() {
        it('is exported and is a function', function() {
            assert.ok(testpilot_subject);
            assert.ok(testpilot_subject.file_0001, 'file_0001 should exist on testpilot_subject');
            const FsWatcherService = testpilot_subject.file_0001.FsWatcherService;
            assert.ok(FsWatcherService, 'FsWatcherService should exist');
            assert.strictEqual(typeof FsWatcherService.prototype.countForConnection, 'function');
        });

            })
})