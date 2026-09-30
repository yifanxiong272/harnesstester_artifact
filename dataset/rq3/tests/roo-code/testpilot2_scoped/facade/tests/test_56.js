let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.MultiPointStrategy.prototype.formatWithoutCachePoints - existence', function(done) {
        // Ensure the function exists and is a function
        let ctor = testpilot_subject && testpilot_subject.file_0006 && testpilot_subject.file_0006.MultiPointStrategy;
        assert.ok(ctor, 'MultiPointStrategy constructor should exist');
        let fn = ctor && ctor.prototype && ctor.prototype.formatWithoutCachePoints;
        assert.strictEqual(typeof fn, 'function', 'formatWithoutCachePoints should be a function');
        done();
    });

    })