let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // use a bit longer timeout in case FS operations are slow on CI
    this.timeout(5000);

    let tmpRoot = null;
    let svc = null;
    let sessions = null;

    beforeEach(async () => {
        // create a temporary directory for each test
        tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'fssvc-test-'));

        // create some files and directories inside it
        fs.mkdirSync(path.join(tmpRoot, 'dirA'));
        fs.writeFileSync(path.join(tmpRoot, 'file1.txt'), 'hello\nworld\n', 'utf8');
        // create a small binary file
        fs.writeFileSync(path.join(tmpRoot, 'bin.dat'), Buffer.from([0x00, 0x01, 0x02, 0x03]));

        // session mock required by FsService
        sessions = {
            get: async (sessionId) => {
                // return minimal metadata shape used by FsService
                return { metadata: { cwd: tmpRoot } };
            }
        };

        // instantiate the service under test
        svc = new testpilot_subject.file_0004.FsService(sessions);
    });

    afterEach(async () => {
        // dispose service if it exposes dispose (class extends Disposable)
        try { svc.dispose(); } catch (e) {}
        // remove temp directory tree
        try {
            // Node 12+ fs.rmSync available; fall back to recursive rmdir if needed
            if (fs.rmSync) {
                fs.rmSync(tmpRoot, { recursive: true, force: true });
            } else {
                // older Node
                const rimraf = (p) => {
                    if (!fs.existsSync(p)) return;
                    for (const name of fs.readdirSync(p)) {
                        const cur = path.join(p, name);
                        const stat = fs.lstatSync(cur);
                        if (stat.isDirectory()) rimraf(cur);
                        else fs.unlinkSync(cur);
                    }
                    fs.rmdirSync(p);
                };
                rimraf(tmpRoot);
            }
        } catch (e) {
            // ignore cleanup errors
        }
        tmpRoot = null;
        svc = null;
        sessions = null;
    });

    it('list should return top-level items (files + directories)', async () => {
        // depth 1 should include immediate children
        const resp = await svc.list('sess', {
            path: '.',
            depth: 1,
            limit: 100,
            show_hidden: true,
            follow_gitignore: false,
            exclude_globs: [],
            sort: undefined,
            include_git_status: false
        });

        // Expect two visible children: dirA, file1.txt, plus bin.dat => 3 entries
        assert.ok(Array.isArray(resp.items), 'items should be an array');
        // Count must be 3 (dirA, file1.txt, bin.dat)
        assert.strictEqual(resp.items.length, 3, `expected 3 items, got ${resp.items.length}`);
    });

    })