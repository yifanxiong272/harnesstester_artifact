let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let fsp = fs.promises;
let os = require('os');
let path = require('path');
let cp = require('child_process');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a temporary directory for each test
    function mktempSync(prefix = 'wtstest-') {
        return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    }

    // Normalize returned path for comparison
    function norm(p) {
        if (!p) return p;
        return path.normalize(p);
    }

    it('finds git root when cwd is inside a nested repo', async function() {
        const tmp = mktempSync();
        try {
            // repo root
            const repoRoot = path.join(tmp, 'myrepo');
            const nested = path.join(repoRoot, 'sub', 'inner');
            // create nested directories
            fs.mkdirSync(nested, { recursive: true });
            // initialize a real git repo in repoRoot so the service detects this repo
            // (creating an empty .git dir isn't always sufficient when there's an outer repo)
            cp.execSync('git init', { cwd: repoRoot, stdio: 'ignore' });

            // create an instance of the service
            const svc = new testpilot_subject.file_0006.WorktreeService();
            const res = await svc.getGitRootPath(nested);
            assert.strictEqual(norm(res), norm(repoRoot));
        } finally {
            // cleanup
            fs.rmSync(tmp, { recursive: true, force: true });
        }
    });

    })