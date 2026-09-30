let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a simple spy function we can inspect.
    function makeSpy() {
        let called = false;
        let callArgs = null;
        const spy = function(...args) {
            called = true;
            callArgs = args;
            return args; // harmless return
        };
        spy.wasCalled = function() { return called; };
        spy.args = function() { return callArgs; };
        return spy;
    }

    it('createSubsystemRuntime should return an object with an exit function and at least one logging method', function() {
        const createSubsystemRuntime = testpilot_subject.file_0015.createSubsystemRuntime;
        assert.strictEqual(typeof createSubsystemRuntime, 'function');

        const runtime = createSubsystemRuntime('unit-test-subsystem', () => {});
        assert.ok(runtime && typeof runtime === 'object', 'runtime should be an object');

        // exit should be a function that the runtime exposes
        assert.strictEqual(typeof runtime.exit, 'function', 'runtime.exit should be a function');

        // Expect at least one common logging method to exist and be a function.
        const loggingCandidates = ['debug', 'info', 'warn', 'error', 'log', 'trace', 'fatal'];
        const hasLoggingMethod = loggingCandidates.some(name => typeof runtime[name] === 'function');
        assert.ok(hasLoggingMethod, 'runtime should expose at least one logging method (debug/info/warn/error/log/trace/fatal)');
    });

    })