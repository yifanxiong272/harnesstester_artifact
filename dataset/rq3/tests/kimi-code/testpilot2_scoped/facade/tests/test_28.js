let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.FsWatcherService.None.dispose', function() {
        it('should exist and be a function', function() {
            // Navigate the expected path safely and assert existence
            assert.ok(testpilot_subject, 'module "testpilot_subject" should be present');

            const file0001 = testpilot_subject.file_0001;
            assert.ok(file0001, 'file_0001 should be present on module');

            const FsWatcherService = file0001.FsWatcherService;
            assert.ok(FsWatcherService, 'FsWatcherService should be present on file_0001');

            const None = FsWatcherService.None;
            assert.ok(None, 'None should be present on FsWatcherService');

            const dispose = None.dispose;
            assert.strictEqual(typeof dispose, 'function', 'dispose should be a function');
        });

            })
})