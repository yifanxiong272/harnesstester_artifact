let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0008.sanitizeHostBaseEnv - empty env', function(done) {
        const fn = testpilot_subject.file_0008.sanitizeHostBaseEnv;
        const env = {};
        const sanitized = fn(env);
        // Should return a new empty object
        assert.deepStrictEqual(sanitized, {});
        assert.notStrictEqual(sanitized, env, 'sanitizeHostBaseEnv should return a new object, not the same reference');
        done();
    });

    })