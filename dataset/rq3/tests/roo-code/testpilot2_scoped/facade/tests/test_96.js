let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const CacheStrategy = testpilot_subject && testpilot_subject.file_0010 && testpilot_subject.file_0010.CacheStrategy;

    it('exports a CacheStrategy constructor/function', function() {
        assert.strictEqual(typeof CacheStrategy, 'function', 'CacheStrategy should be a function (constructor or factory)');
    });

    // Helper to construct an instance trying both `new` and direct call so tests work
    // whether CacheStrategy is a class, constructor function, or factory function.
    function makeInstance(config) {
        // Prefer `new` for classes; if it throws, try calling as a function.
        try {
            return new CacheStrategy(config);
        } catch (e) {
            return CacheStrategy(config);
        }
    }

    })