let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0015.resolveShellFromEnv', function() {
    it('prefers SHELL over COMSPEC when both are present', function() {
        const env = { SHELL: 'bash', COMSPEC: 'C:\\Windows\\cmd.exe' };
        const result = testpilot_subject.file_0015.resolveShellFromEnv(env);
        assert.strictEqual(result, env.SHELL);
    });

    })