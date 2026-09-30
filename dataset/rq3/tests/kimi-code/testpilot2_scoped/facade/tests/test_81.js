let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const flush = testpilot_subject.file_0001.FsWatcherService.prototype.flushWindow;

    it('does nothing when session is missing', function() {
        const sessions = new Map();
        const ctx = {
            sessions,
            lookup: { resolve: () => { throw new Error('should not be called'); } },
            debounceMs: 50,
            logger: { warn: () => {} }
        };

        // should not throw
        flush.call(ctx, 'non-existent-session');
        assert.strictEqual(sessions.size, 0);
    });

    })