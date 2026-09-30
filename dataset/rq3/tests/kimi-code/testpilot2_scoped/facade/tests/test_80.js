let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0001.FsWatcherService.prototype.flushWindow', function() {
        // Helper to safely call flushWindow and normalize sync/async returns to a Promise
        function callFlushSafely(inst, sessionId) {
            try {
                let res = inst.flushWindow(sessionId);
                if (res && typeof res.then === 'function') {
                    return res;
                }
                return Promise.resolve(res);
            } catch (err) {
                return Promise.reject(err);
            }
        }

        let FsWatcherService;
        before(function() {
            // Resolve constructor if available
            FsWatcherService = testpilot_subject &&
                             testpilot_subject.file_0001 &&
                             testpilot_subject.file_0001.FsWatcherService;
            if (!FsWatcherService) {
                // If the target is not present, skip the whole suite
                this.skip();
            }
        });

        it('should expose flushWindow on the prototype as a function', function() {
            assert.ok(FsWatcherService, 'FsWatcherService constructor missing');
            assert.ok(FsWatcherService.prototype, 'FsWatcherService.prototype missing');
            assert.strictEqual(typeof FsWatcherService.prototype.flushWindow, 'function',
                'flushWindow should be a function on the prototype');
        });

            })
})