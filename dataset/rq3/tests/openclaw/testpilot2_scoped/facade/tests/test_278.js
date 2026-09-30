let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0008.validateHostEnv', function() {
    it('does not throw for a safe environment variable', function() {
        // a normal harmless env var should be allowed
        const env = { 'MY_SAFE_VAR': 'value' };
        // should not throw
        testpilot_subject.file_0008.validateHostEnv(env);
    });

    })