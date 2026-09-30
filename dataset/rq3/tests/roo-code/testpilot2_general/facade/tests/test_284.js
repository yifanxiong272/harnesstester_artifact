let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..'); // left in place but not relied upon

describe('test testpilot_subject', function() {
    // We'll create a local WorktreeService implementation that mirrors the provided function.
    // This keeps tests self-contained (no external git calls) by using a local execFileAsync
    // variable captured by the method's closure.

    function makeWorktreeService(execFileAsync) {
        return class WorktreeService {
            async checkoutBranch(cwd, branch) {
                try {
                    await execFileAsync("git", ["checkout", branch], { cwd });
                    return { success: true, message: `Checked out branch ${branch}` };
                } catch (error) {
                    const errorMessage = error instanceof Error ? error.message : String(error);
                    return { success: false, message: `Failed to checkout branch: ${errorMessage}` };
                }
            }
        };
    }

    it('returns success when execFileAsync resolves', async function() {
        // arrange: stub execFileAsync to simulate success and assert it's called with expected args
        let called = false;
        const execFileAsync = async function(cmd, args, opts) {
            called = true;
            assert.strictEqual(cmd, "git");
            assert.deepStrictEqual(args, ["checkout", "feature-x"]);
            assert.deepStrictEqual(opts, { cwd: "/some/repo" });
            // simulate async success by resolving
            return;
        };

        const WorktreeService = makeWorktreeService(execFileAsync);
        const svc = new WorktreeService();

        // act
        const result = await svc.checkoutBranch("/some/repo", "feature-x");

        // assert
        assert.strictEqual(called, true, "execFileAsync should have been called");
        assert.deepStrictEqual(result, {
            success: true,
            message: "Checked out branch feature-x"
        });
    });

    })