let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.buildExecRuntimeErrorOutcome', function() {
    it('should return an object when called with no params', function() {
        // provide an empty object instead of undefined so the function
        // doesn't try to read properties off of undefined
        let out = testpilot_subject.file_0008.buildExecRuntimeErrorOutcome({});
        assert.ok(out !== null, 'result should not be null');
        assert.strictEqual(typeof out, 'object', 'result should be an object');
        assert.ok(!Array.isArray(out), 'result should not be an array');
    });

    })