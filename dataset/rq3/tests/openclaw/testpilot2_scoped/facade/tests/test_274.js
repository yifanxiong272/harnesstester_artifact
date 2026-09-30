let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    describe('file_0008.sanitizeHostBaseEnv', function() {
        it('should be deterministic: same input yields deeply equal outputs', function() {
            let env = { HOST: 'Example.COM', PORT: '8080', EXTRA: null, NUM: 42 };
            let first = testpilot_subject.file_0008.sanitizeHostBaseEnv(env);
            let second = testpilot_subject.file_0008.sanitizeHostBaseEnv(env);
            assert.deepStrictEqual(first, second, 'sanitizeHostBaseEnv should be deterministic for same input');
        });

            })
})