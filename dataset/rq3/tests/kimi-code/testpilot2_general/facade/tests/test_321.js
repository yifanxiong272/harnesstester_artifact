let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // get the raw method from the prototype so we don't need to construct the full service
    const resolvePath = testpilot_subject.file_0004.FsService.prototype.resolvePath;

    // helper to create a temp dir for each test
    function makeTempDir(prefix = 'tst-') {
        return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    }

    function removeDirRecursive(dir) {
        try {
            // prefer fs.rmSync when available (Node 14.14+/16+)
            if (fs.rmSync) {
                fs.rmSync(dir, { recursive: true, force: true });
            } else {
                // older Node fallback
                const rimraf = (p) => {
                    if (!fs.existsSync(p)) return;
                    for (const entry of fs.readdirSync(p)) {
                        const cur = path.join(p, entry);
                        if (fs.lstatSync(cur).isDirectory()) rimraf(cur);
                        else fs.unlinkSync(cur);
                    }
                    fs.rmdirSync(p);
                };
                rimraf(dir);
            }
        } catch (e) {
            // best-effort cleanup; swallow errors to not mask test failures
        }
    }

    it('resolvePath returns correct absolute, relative and isDirectory for a file', async function() {
        const tmp = makeTempDir();
        try {
            const filePath = path.join(tmp, 'file.txt');
            fs.writeFileSync(filePath, 'hello');

            // minimal session store that the method expects
            const sessions = {
                get: async (id) => ({ metadata: { cwd: tmp } })
            };
            const ctx = { sessions };

            const res = await resolvePath.call(ctx, 'any-session', 'file.txt');

            assert.strictEqual(res.absolute, filePath, 'absolute path should match the created file');
            assert.strictEqual(res.relative, path.relative(tmp, filePath), 'relative path should be relative to cwd');
            assert.strictEqual(res.isDirectory, false, 'file should not be reported as directory');
        } finally {
            removeDirRecursive(tmp);
        }
    });

    })