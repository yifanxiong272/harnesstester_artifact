let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsWatcherService = testpilot_subject &&
        testpilot_subject.file_0001 &&
        testpilot_subject.file_0001.FsWatcherService;

    it('FsWatcherService.removePaths should exist and have arity 3', function() {
        assert.ok(FsWatcherService, 'FsWatcherService constructor is available');
        const fn = FsWatcherService.prototype && FsWatcherService.prototype.removePaths;
        assert.ok(typeof fn === 'function', 'removePaths is a function on the prototype');
        // arity check — most implementations expect (sessionId, connectionId, absPaths)
        assert.strictEqual(fn.length, 3);
    });

    // Helper to create an instance without relying on constructor parameters.
    function makeInstance() {
        try {
            // Prefer real construction if possible
            return new FsWatcherService();
        } catch (e) {
            // Fall back to a plain object whose prototype is the service prototype.
            // This allows calling prototype methods without invoking constructor side effects.
            return Object.create(FsWatcherService.prototype || {});
        }
    }

    function isThenable(obj) {
        return obj && (typeof obj.then === 'function');
    }

    })