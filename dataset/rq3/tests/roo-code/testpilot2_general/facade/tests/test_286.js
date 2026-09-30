let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0006.WorktreeService.prototype.parseWorktreeOutput - single entry, current match', function(done) {
        const WorktreeService = testpilot_subject.file_0006 && testpilot_subject.file_0006.WorktreeService;
        assert(WorktreeService, 'WorktreeService constructor not found on testpilot_subject.file_0006');

        const svc = new WorktreeService();
        // Provide a simple normalizePath implementation for consistency in tests
        svc.normalizePath = p => (p || '').replace(/\/+$/, '');

        const output = [
            'worktree /repo/wt1',
            'HEAD abcdef123456',
            'branch refs/heads/main'
        ].join('\n');

        const parsed = svc.parseWorktreeOutput(output, '/repo/wt1');

        assert.strictEqual(Array.isArray(parsed), true, 'result should be an array');
        assert.strictEqual(parsed.length, 1, 'should parse one worktree');

        const wt = parsed[0];
        assert.strictEqual(wt.path, '/repo/wt1');
        assert.strictEqual(wt.commitHash, 'abcdef123456');
        assert.strictEqual(wt.branch, 'main'); // refs/heads/ should be stripped
        assert.strictEqual(wt.isCurrent, true);
        assert.strictEqual(wt.isBare, false);
        assert.strictEqual(wt.isDetached, false);
        assert.strictEqual(wt.isLocked, false);

        done();
    });

    })