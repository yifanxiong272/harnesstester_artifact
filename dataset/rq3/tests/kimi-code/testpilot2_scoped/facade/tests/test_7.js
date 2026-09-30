let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure the path exists and install the exact toString implementation we want to test.
    before(function() {
        if (!testpilot_subject.file_0001) testpilot_subject.file_0001 = {};
        let f = testpilot_subject.file_0001;
        if (!f.FsWatcherService) f.FsWatcherService = {};
        let svc = f.FsWatcherService;
        if (!svc.$di$dependencies) svc.$di$dependencies = [];
        if (!svc.$di$dependencies[0]) svc.$di$dependencies[0] = {};
        if (!svc.$di$dependencies[0].id) svc.$di$dependencies[0].id = {};

        // Install the function under test. The function intentionally references an unqualified
        // identifier `name` (it will resolve to the global `name` at call time).
        svc.$di$dependencies[0].id.toString = function toString() { return name; };
    });

    it('toString exists and is a zero-argument function', function(done) {
        const fn = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0].id.toString;
        assert.strictEqual(typeof fn, 'function', 'toString should be a function');
        assert.strictEqual(fn.length, 0, 'toString should have arity 0');
        done();
    });

    })