let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to obtain an object that has the prototype method without
    // depending on constructor parameter semantics.
    function getStrategyInstance() {
        const ctor = testpilot_subject && testpilot_subject.file_0006 && testpilot_subject.file_0006.MultiPointStrategy;
        assert.ok(ctor, 'MultiPointStrategy constructor must exist');

        // Prefer creating a real instance, but if the constructor requires arguments
        // or throws, fall back to an object whose prototype is the constructor's prototype.
        try {
            return new ctor();
        } catch (e) {
            return Object.create(ctor.prototype);
        }
    }

    it('should expose determineMessageCachePoints as a function', function() {
        const strategy = getStrategyInstance();
        assert.strictEqual(typeof strategy.determineMessageCachePoints, 'function');
    });

    })