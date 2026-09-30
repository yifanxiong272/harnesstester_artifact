let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to decide whether the function returned a new env object or modified the given one
    function pathHolderFromResult(result, originalEnv) {
        if (result && (typeof result === 'object')) return result;
        return originalEnv;
    }

    it('should add shellPath to existing PATH (path appears as a segment)', function() {
        let env = { PATH: '/usr/bin:/bin' };
        let shellPath = '/custom/shell';
        let result = testpilot_subject.file_0009.applyShellPath(env, shellPath);

        let holder = pathHolderFromResult(result, env);
        assert.ok(holder.PATH, 'PATH should exist after applyShellPath');

        // PATH separator may be ':' (POSIX) or ';' (Windows). Split on either.
        let parts = holder.PATH.spl    })
})