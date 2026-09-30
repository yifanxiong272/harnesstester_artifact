let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.buildExecRuntimeErrorOutcome', function() {
    it('should return distinct objects for repeated calls (no shared reference)', function() {
        let params = { message: 'repeat test' };
        let a = testpilot_subject.file_0008.buildExecRuntimeErrorOutcome(params);
        let b = testpilot_subject.file_0008.buildExecRuntimeErrorOutcome(params);
        // They should not be the identical reference
        assert.notStrictEqual(a, b, 'two calls should not return the same object reference');
        // But they should both be objects
        assert.strictEqual(typeof a, 'object');
        assert.strictEqual(typeof b, 'object');
    });

    })