let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0015.resolveShellFromEnv', function() {
        it('returns "zsh" for a typical zsh path', function() {
            const env = { SHELL: '/bin/zsh' };
            const result = testpilot_subject.file_0015.resolveShellFromEnv(env);
            assert.strictEqual(result, 'zsh');
        });

            })
})