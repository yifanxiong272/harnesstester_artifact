let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0015.resolveShellFromEnv', function() {
    it('does not mutate the provided env object', function() {
        const env = { SHELL: '/bin/ksh', FOO: 'bar' };
        const snapshot = Object.assign({}, env);
        testpilot_subject.file_0015.resolveShellFromEnv(env);
        assert.deepStrictEqual(env, snapshot, 'resolveShellFromEnv should not modify the env object');
    });
});