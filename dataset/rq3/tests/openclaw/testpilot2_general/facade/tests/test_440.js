let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0015.runtimeForLogger: basic logger methods forward to provided logger', function() {
        // capture calls to the provided logger
        let calls = [];
        let logger = {
            info: function() { calls.push(['info', Array.from(arguments)]); },
            warn: function() { calls.push(['warn', Array.from(arguments)]); },
            debug: function() { calls.push(['debug', Array.from(arguments)]); },
            error: function() { calls.push(['error', Array.from(arguments)]); }
        };

        // Provide an exit stub that should not be called in this test
        let exitCalled = false;
        function exitStub() { exitCalled = true; }

        // create runtime
        let rt = testpilot_subject.file_0015.runtimeForLogger(logger, exitStub);

        // Helper to get method if present on returned runtime or on the function itself
        function methodOf(obj, name) {
            if (!obj) return null;
            if (typeof obj[name] === 'function') return obj[name].bind(obj);
            return null;
        }

        // Try to call common logging methods if they exist
        let info = methodOf(rt, 'info');
        let warn = methodOf(rt, 'warn');
        let debug = methodOf(rt, 'debug');
        let error = methodOf(rt, 'error');

        // At least one of these should be present for a reasonable runtime wrapper
        assert(info || warn || debug || error, 'returned runtime should expose at least one logging method');

        if (info) info('hello', 1);
        if (warn) warn('be careful');
        if (debug) debug({k: 'v'});
        if (error) error('boom');

        // Ensure provided logger received the forwarded calls in the same order
        // We only assert for calls that we actually invoked above.
        let expected = [];
        if (info) expected.push(['info', ['hello', 1]]);
        if (warn) expected.push(['warn', ['be careful']]);
        if (debug) expected.push(['debug', [{k: 'v'}]]);
        if (error) expected.push(['error', ['boom']]);

        assert.deepStrictEqual(calls, expected);
        assert.strictEqual(exitCalled, false, 'exit should not have been invoked by logging methods');
    });

    })