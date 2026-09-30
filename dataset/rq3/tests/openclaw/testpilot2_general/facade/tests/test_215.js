let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call the function and normalize whether it mutates env or returns a new env.
    function callApply(env, prepend, options) {
        // Make a shallow clone to pass in so tests can reason about original vs returned easily.
        let envCopy = Object.assign({}, env);
        let res = testpilot_subject.file_0009.applyPathPrepend(envCopy, prepend, options);
        // If function returns undefined, assume it mutated the passed object in-place.
        if (typeof res === 'undefined' || res === null) {
            return envCopy;
        }
        // If it returned something, prefer that (could be same object or a new object).
        return res;
    }

    it('prepends multiple entries (array) to an existing PATH-like variable preserving order', function() {
        let delim = path.delimiter;
        let env = { PATH: '/usr/bin' };
        let prepend = ['/a', '/b'];
        let resultEnv = callApply(env, prepend, {});
        assert.strictEqual(resultEnv.PATH, ['/a', '/b', env.PATH].join(delim));
    });

    })