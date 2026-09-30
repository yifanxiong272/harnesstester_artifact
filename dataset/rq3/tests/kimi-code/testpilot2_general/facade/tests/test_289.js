let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let os = require('os');
let fs = require('fs').promises;
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0004.FsService.prototype.list', function() {
    // Increase timeout for filesystem operations on slower systems
    this.timeout(5000);

    // Helper to create a temporary test tree
    async function makeTestTree(structure, baseDir) {
        // structure is an object where keys are file/dir names.
        // If value is null -> file with sample contents.
        // If value is object -> directory with nested structure.
        for (const name of Object.keys(structure)) {
            const val = structure[name];
            const p = path.join(baseDir, name);
            if (val === null) {
                await fs.writeFile(p, `contents of ${name}`);
            } else if (typeof val === 'object') {
                await fs.mkdir(p);
                await makeTestTree(val, p);
            }
        }
    }

    it('lists top-level entries and includes children_by_path when depth>1', async function() {
        const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'fs-list-test-'));
        try {
            // Create structure:
            // tmp/
            //   a.txt
            //   sub/
            //     b.txt
            //   .hidden
            await makeTestTree({
                'a.txt': null,
                'sub': { 'b.txt': null },
                '.hidden': null
            }, tmp);

            // Instantiate service and stub sessions.get to return our cwd
            const FsService = testpilot_subject.file_0004.FsService;
            const svc = new FsService();
            svc.sessions = {
                get: async (id) => ({ metadata: { cwd: tmp } })
            };

            // Call list with depth 2 to capture children_by_path
            const req = {
                path: '.',
                depth: 2,
                limit: 100,
                show_hidden: false,
                follow_gitignore: false,
                sort: 'name',
                exclude_globs: undefined
            };

            const res = await svc.list('session-id', req);

            // items should include 'a.txt' and 'sub' but NOT '.hidden'
            const itemNames = res.items.map(i => i.name || i.basename || i.path || i.relpath).filter(Boolean);
            // The exact property name for the filename in fsEntry might vary (e.g., name/basename/path),
            // so also inspect a common fallback: try to reconstruct from returned entries
            const itemsBasenames = res.items.map(i => {
                if (i.name) return i.name;
                if (i.basename) return i.basename;
                if (i.path) return path.basename(i.path);
                if (i.relative_path) return path.basename(i.relative_path);
                // fallback: if entry has an absolute path
                if (i.absolute_path) return path.basename(i.absolute_path);
                return null;
            });

            assert(itemsBasenames.includes('a.txt'), 'a.txt should be listed in items');
            assert(itemsBasenames.includes('sub'), 'sub directory should be listed in items');
            assert(!itemsBasenames.includes('.hidden'), '.hidden should be hidden when show_hidden is false');

            // children_by_path should contain the 'sub' key with its child 'b.txt'
            assert(res.children_by_path, 'children_by_path should be present for depth>1');

            // The key for top-level directories is their relative path. For 'sub' it should be 'sub'.
            const childrenKeys = Object.keys(res.children_by_path);
            assert(childrenKeys.includes('sub'), `children_by_path should include 'sub' (keys: ${childrenKeys})`);

            const subChildren = res.children_by_path['sub'];
            const subBasenames = subChildren.map(ch => {
                if (ch.name) return ch.name;
                if (ch.basename) return ch.basename;
                if (ch.path) return path.basename(ch.path);
                if (ch.relative_path) return path.basename(ch.relative_path);
                if (ch.absolute_path) return path.basename(ch.absolute_path);
                return null;
            });
            assert(subBasenames.includes('b.txt'), 'b.txt should appear under children_by_path["sub"]');

            // truncated should be false with a high limit
            assert.strictEqual(res.truncated, false);
        } finally {
            // cleanup
            await fs.rm(tmp, { recursive: true, force: true });
        }
    });

    })