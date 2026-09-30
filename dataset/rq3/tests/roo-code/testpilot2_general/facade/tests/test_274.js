let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0006.WorktreeService.prototype.deleteWorktree', function() {
        let svc;
        let originalExecFileAsyncModule;
        let originalGlobalExecFileAsync;

        beforeEach(function() {
            svc = new testpilot_subject.file_0006.WorktreeService();

            // Save any existing execFileAsync references so we can restore them
            originalExecFileAsyncModule = testpilot_subject.file_0006.execFileAsync;
            originalGlobalExecFileAsync = global.execFileAsync;

            // Provide harmless defaults for methods we will override in tests
            svc.normalizePath = p => (p || '').replace(/\\/g, '/');
        });

        afterEach(function() {
            // Restore any overwritten execFileAsync
            try { testpilot_subject.file_0006.execFileAsync = originalExecFileAsyncModule; } catch (_) {}
            try { global.execFileAsync = originalGlobalExecFileAsync; } catch (_) {}
        });

        it('returns failure when git worktree remove throws', async function() {
            const cwd = '/repo3';
            const worktreePath = '/repo3/wt-bad';
            svc.listWorktrees = async (c) => {
                assert.strictEqual(c, cwd);
                return [
                    { path: worktreePath, branch: 'will-not-delete' }
                ];
            };

            // Simulate execFileAsync throwing on the worktree remove call
            let callCount = 0;
            const stubExec = async function(cmd, args, opts) {
                callCount++;
                if (callCount === 1) {
                    // fail the worktree remove
                    throw new Error('git failed to remove worktree');
                }
                // if branch deletion attempted, just succeed
                return '';
            };

            testpilot_subject.file_0006.execFileAsync = stubExec;
            global.execFileAsync = stubExec;

            const result = await svc.deleteWorktree(cwd, worktreePath);
            assert.strictEqual(result.success, false, 'expected failure when git remove fails');

            // Accept either the service's own "Failed to delete worktree" text or the original git error text.
            const msg = result && result.message ? String(result.message) : '';
            assert.ok(
                msg.includes('Failed to delete worktree') || msg.includes('git failed to remove worktree'),
                `expected message to include either "Failed to delete worktree" or "git failed to remove worktree", got: ${msg}`
            );
        });
    });
});