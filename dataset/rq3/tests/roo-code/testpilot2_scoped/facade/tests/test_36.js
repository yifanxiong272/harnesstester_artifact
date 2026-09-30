let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.MultiPointStrategy.prototype.determineOptimalCachePoints', function() {
    // Grab the function under test from the prototype so we can call it
    // with a minimal context. This avoids depending on any constructor behavior.
    const fn = testpilot_subject &&
               testpilot_subject.file_0006 &&
               testpilot_subject.file_0006.MultiPointStrategy &&
               testpilot_subject.file_0006.MultiPointStrategy.prototype &&
               testpilot_subject.file_0006.MultiPointStrategy.prototype.determineOptimalCachePoints;

    it('function should exist', function() {
        assert.ok(fn, 'determineOptimalCachePoints must be present on the prototype');
        assert.strictEqual(typeof fn, 'function', 'determineOptimalCachePoints must be a function');
    });

    })