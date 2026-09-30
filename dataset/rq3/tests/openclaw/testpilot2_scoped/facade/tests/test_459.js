let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0015.resolveShellFromEnv', function() {
    it('returns env.SHELL when SHELL is present', function() {
        const env = { SHELL: 'zsh' };
        const result = testpilot_subject.file_0015.resolveShellFromEnv(env);
        assert.strictEqual(result, env.SHELL);
    });

    })