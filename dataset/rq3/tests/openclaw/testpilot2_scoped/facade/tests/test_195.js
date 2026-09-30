let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0008.applyPathPrepend', function() {
        const fn = testpilot_subject && testpilot_subject.file_0008 && testpilot_subject.file_0008.applyPathPrepend;

        it('exists and is a function', function() {
            assert.ok(fn, 'applyPathPrepend should be defined');
            assert.equal(typeof fn, 'function', 'applyPathPrepend should be a function');
        });

        // Helper to accept implementations that either mutate env in-place or return a new object
        function applyAndGetResult(env, prepend, options) {
            // Work on a deep clone so we can compare originals if needed
            const clone = JSON.parse(JSON.stringify(env));
            const ret = fn(clone, prepend, options);
            return (ret === undefined) ? clone : ret;
        }

            })
})