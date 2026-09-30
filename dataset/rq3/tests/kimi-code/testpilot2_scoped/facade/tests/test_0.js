let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    function isPromise(obj) {
        return !!obj && (typeof obj.then === 'function');
    }

    // helper to call a method that may be sync or return a Promise
    function callMaybeAsync(fn) {
        try {
            let res = fn();
            if (isPromise(res)) return res;
            return Promise.resolve(res);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('exports FsWatcherService as a constructor/function and can be instantiated with minimal mocks', function() {
        let C = testpilot_subject && testpilot_subject.file_0001 && testpilot_subject.file_0001.FsWatcherService;
        assert.strictEqual(typeof C, 'function', 'FsWatcherService should be a function/constructor');

        // Provide simple mocks for dependencies; tests must be self-contained
        let lookup = {};
        let options = {};
        let logger = {
            debug: function() {},
            info: function() {},
            warn: function() {},
            error: function() {}
        };
        let sessionService = {};

        let inst = new C(lookup, options, logger, sessionService);
        assert.ok(inst && typeof inst === 'object', 'instance should be an object');
    });

    })