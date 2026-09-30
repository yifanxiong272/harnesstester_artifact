let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // utility to create a temporary directory for tests
    function makeTempDir(prefix = 'fsservice-') {
        return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    }

    // recursive rm helper for Node versions that support it; fallback to manual removal
    function removeDir(dir) {
        try {
            fs.rmSync(dir, { recursive: true, force: true });
        } catch (e) {
            // fallback: best-effort manual removal
            try {
                if (fs.existsSync(dir)) {
                    const entries = fs.readdirSync(dir);
                    for (const entry of entries) {
                        const entryPath = path.join(dir, entry);
                        const stat = fs.lstatSync(entryPath);
                        if (stat.isDirectory()) {
                            removeDir(entryPath);
                        } else {
                            fs.unlinkSync(entryPath);
                        }
                    }
                    fs.rmdirSync(dir);
                }
            } catch (e2) {
                // ignore
            }
        }
    }

    it('test testpilot_subject.file_0004.FsService.prototype.matcher - default .git/ added and cache set', async function() {
        const tmp = makeTempDir();
        try {
            // instantiate service
            const Service = testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService;
            assert(Service, 'FsService constructor not found on testpilot_subject.file_0004');
            const svc = new Service();

            // ensure there's a gitignoreCache Map available
            if (!svc.gitignoreCache || typeof svc.gitignoreCache.get !== 'function') {
                svc.gitignoreCache = new Map();
            }

            // Call matcher on a directory that has no .gitignore file
            const ig = await svc.matcher(tmp);
            assert(ig, 'matcher did not return an ignore instance');

            // The implementation always adds ".git/" so files under .git should be ignored
            assert.strictEqual(typeof ig.ignores, 'function', 'returned object does not have ignores()');
            assert.strictEqual(ig.ignores('.git/HEAD'), true, '.git/HEAD should be ignored by default');
            assert.strictEqual(ig.ignores('some/random/file.txt'), false, 'non-matching path should not be ignored');

            // The returned ignore instance should be cached under the same realCwd key
            const cached = svc.gitignoreCache.get(tmp);
            assert.strictEqual(cached, ig, 'returned ignore instance should be stored in gitignoreCache');
        } finally {
            removeDir(tmp);
        }
    });

    })