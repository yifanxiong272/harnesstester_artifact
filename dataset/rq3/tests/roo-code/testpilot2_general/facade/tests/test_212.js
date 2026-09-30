let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject && testpilot_subject.file_0005 && testpilot_subject.file_0005.exposeSourceMapsForDebugging;

    function isThenable(x) {
        return x && (typeof x === 'object' || typeof x === 'function') && typeof x.then === 'function';
    }

    // Call a possibly-sync-or-async function and always return a Promise that resolves to its value.
    function callMaybeAsync(func, ...args) {
        try {
            const result = func.apply(null, args);
            if (isThenable(result)) {
                return result;
            } else {
                return Promise.resolve(result);
            }
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('exposeSourceMapsForDebugging should be present and be a function', function() {
        assert.ok(fn, 'expected testpilot_subject.file_0005.exposeSourceMapsForDebugging to exist');
        assert.strictEqual(typeof fn, 'function', 'exposeSourceMapsForDebugging should be a function');
    });

    })