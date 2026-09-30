let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const FsWatcherService = testpilot_subject &&
                              testpilot_subject.file_0001 &&
                              testpilot_subject.file_0001.FsWatcherService;

    it('exports FsWatcherService constructor/function', function() {
        assert.ok(FsWatcherService, 'FsWatcherService should be exported');
        assert.strictEqual(typeof FsWatcherService, 'function', 'FsWatcherService should be a constructor (function)');
        assert.strictEqual(typeof FsWatcherService.prototype.dispose, 'function',
            'FsWatcherService.prototype.dispose should be a function');
    });

    // Helper to create an instance without depending on constructor behavior:
    function makeInstance() {
        try {
            // Try normal construction first
            return new FsWatcherService();
        } catch (e) {
            // If constructor requires arguments or throws, create a bare object with the right prototype.
            // This lets us exercise prototype.dispose without invoking constructor side-effects.
            return Object.create(FsWatcherService.prototype);
        }
    }

    })