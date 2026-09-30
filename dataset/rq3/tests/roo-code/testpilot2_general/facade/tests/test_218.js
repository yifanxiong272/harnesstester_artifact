let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    // Keep originals to restore after each test
    const originalExec = child_process.exec;
    const originalExecSync = child_process.execSync;
    const originalSpawnSync = child_process.spawnSync;

    afterEach(function() {
        // Restore original functions to avoid leaking stubs across tests
        child_process.exec = originalExec;
        child_process.execSync = originalExecSync;
        child_process.spawnSync = originalSpawnSync;
    });

    // Helper to get a callable checkGitInstalled regardless of constructor requirements.
    const getCheckGitInstalled = () => {
        const WorktreeService = testpilot_subject.file_0006.WorktreeService;
        // Bind method to a plain object to avoid running potentially unknown constructor logic.
        return WorktreeService.prototype.checkGitInstalled.bind({});
    };

    it('resolves when git is available via child_process.exec (callback style)', async function() {
        // Stub exec to simulate successful "git --version"
        child_process.exec = function(cmd, opts, cb) {
            if (typeof opts === 'function') { cb = opts; }
            process.nextTick(() => cb(null, 'git version 2.30.0\n', ''));
            // return a dummy child object to match exec's usual return
            return { stdout: '' };
        };

        const checkGitInstalled = getCheckGitInstalled();
        // Should resolve (not throw). If it throws, the test will fail.
        await checkGitInstalled();
    });

    })