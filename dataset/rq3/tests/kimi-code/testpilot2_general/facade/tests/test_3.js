let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout for filesystem ops on slow CI
    this.timeout(5000);

    let tmpRoot;
    let sessions;
    let logger;
    let service;

    // Helper to create temp dir
    async function makeTempDir() {
        const prefix = path.join(os.tmpdir(), 'fssearch-test-');
        return await fs.promises.mkdtemp(prefix);
    }

    // Helper to remove directory recursively (works on modern Node)
    async function removeDir(dir) {
        try {
            if (fs.promises.rm) {
                await fs.promises.rm(dir, { recursive: true, force: true });
            } else {
                // fallback
                await fs.promises.rmdir(dir, { recursive: true });
            }
        } catch (e) {
            // ignore
        }
    }

    beforeEach(async () => {
        tmpRoot = await makeTempDir();
        // simple sessions mock
        sessions = {
            get: async (id) => {
                return { metadata: { cwd: tmpRoot } };
            }
        };
        // simple logger mock
        logger = { warn: (m) => { /* noop */ } };

        service = new testpilot_subject.file_0002.FsSearchService(sessions, logger);
    });

    afterEach(async () => {
        if (service && typeof service.dispose === 'function') {
            service.dispose();
        }
        await removeDir(tmpRoot);
    });

    it('search should find files by fuzzy name match', async () => {
        // Create files and directories
        await fs.promises.writeFile(path.join(tmpRoot, 'foo.txt'), 'alpha');
        await fs.promises.writeFile(path.join(tmpRoot, 'bar.md'), 'beta');
        await fs.promises.mkdir(path.join(tmpRoot, 'sub'));
        await fs.promises.writeFile(path.join(tmpRoot, 'sub', 'foobar.js'), 'gamma');

        const req = {
            query: 'foo',
            follow_gitignore: false,
            include_globs: undefined,
            exclude_globs: undefined,
            limit: 10
        };

        const out = await service.search('ignored-session-id', req);

        // should find foo.txt and sub/foobar.js (order by score then path)
        assert.ok(Array.isArray(out.items), 'items should be array');
        const paths = out.items.map(i => i.path).sort();
        assert.deepStrictEqual(paths, ['foo.txt', 'sub/foobar.js']);
        assert.strictEqual(out.truncated, false);
    });

    })