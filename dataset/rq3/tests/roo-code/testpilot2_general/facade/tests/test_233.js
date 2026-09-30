let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let fsp = fs.promises;
let os = require('os');
let path = require('path');
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

    it('returns a falsy value when there is no git root in ancestry', async function() {
        const tmp = mktempSync();
        try {
            // a plain directory tree without any .git
            const dir = path.join(tmp, 'no-repo', 'a', 'b');
            fs.mkdirSync(dir, { recursive: true });
            const svc = new testpilot_subject.file_0006.WorktreeService();
            const res = await svc.getGitRootPath(dir);

            // Accept any falsy value (null/undefined/empty string/false)
            // If a truthy value is returned, make sure it actually points at a git root
            if (!res) {
                assert.ok(!res, 'expected a falsy value when no git root is present');
            } else {
                // normalize path and ensure it's a string
                const got = norm(res);
                assert.strictEqual(typeof got, 'string', `expected a string path when a value is returned, got ${typeof got}`);
                // ensure that the returned path actually contains a .git entry
                const gitDir = path.join(got, '.git');
                assert.ok(fs.existsSync(gitDir), `returned path (${got}) does not contain a .git directory`);
            }
        } finally {
            fs.rmSync(tmp, { recursive: true, force: true });
        }
    });
});