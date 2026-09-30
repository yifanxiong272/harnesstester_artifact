let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let path = require('path');

describe('test testpilot_subject', function() {
    // Keep originals to restore after tests
    const origExecAsync = global.execAsync;
    const origExecFileAsync = global.execFileAsync;

    after(function() {
        // Restore globals in case other tests rely on them
        global.execAsync = origExecAsync;
        global.execFileAsync = origExecFileAsync;
    });

    it('parseWorktreeOutput and normalizePath should parse various flags and detect current worktree', async function() {
        const svc = new testpilot_subject.file_0006.WorktreeService();

        const sampleOutput = [
            "worktree /repo/other",
            "HEAD 0123456789abcdef",
            "branch refs/heads/feature-xyz",
            "",
            "worktree /repo/current/",
            "HEAD abcdef0123456789",
            "branch refs/heads/main",
            "detached",
            "locked some lock reason"
        ].join("\n");

        const parsed = svc.parseWorktreeOutput(sampleOutput, "/repo/current");

        // Expect two worktrees parsed
        assert.strictEqual(parsed.length, 2);

        const wt0 = parsed.find(w => svc.normalizePath(w.path) === svc.normalizePath("/repo/other"));
        const wt1 = parsed.find(w => svc.normalizePath(w.path) === svc.normalizePath("/repo/current/"));

        // First worktree assertions
        assert.ok(wt0, "first worktree not found");
        assert.strictEqual(wt0.commitHash, "0123456789abcdef");
        assert.strictEqual(wt0.branch, "feature-xyz");
        assert.strictEqual(!!wt0.isDetached, false);
        assert.strictEqual(!!wt0.isLocked, false);
        assert.strictEqual(wt0.isCurrent, false);

        // Second worktree assertions
        assert.ok(wt1, "second worktree not found");
        assert.strictEqual(wt1.commitHash, "abcdef0123456789");
        assert.strictEqual(wt1.branch, "main");
        assert.strictEqual(wt1.isDetached, true);
        assert.strictEqual(wt1.isLocked, true);
        assert.strictEqual(wt1.lockReason, "some lock reason");
        assert.strictEqual(wt1.isCurrent, true);

        // normalizePath should remove trailing slash but preserve root-like paths
        const withSlash = "/some/path/";
        const withoutSlash = svc.normalizePath(withSlash);
        assert.strictEqual(withoutSlash, path.normalize("/some/path"));
    });

    })