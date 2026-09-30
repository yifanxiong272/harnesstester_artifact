let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let os = require('os');
let fs = require('fs').promises;
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // temporary directories created for tests will be removed after the suite
    let tmpDirs = [];

    // helper to create a temporary directory
    async function makeTmpDir() {
        const base = await fs.mkdtemp(path.join(os.tmpdir(), 'tp-'));
        tmpDirs.push(base);
        return base;
    }

    after(async function() {
        // cleanup all temporary directories created during tests
        for (const d of tmpDirs) {
            // Node 12+ supports recursive rm with force
            try {
                await fs.rm(d, { recursive: true, force: true });
            } catch (e) {
                // best-effort cleanup
            }
        }
    });

    it('creates nested file when mkdir=true and appends a string', async function() {
        const root = await makeTmpDir();
        const rel = path.join('nested', 'dir', 'file.txt');

        await testpilot_subject.file_0018.appendFileWithinRoot({
            rootDir: root,
            relativePath: rel,
            mkdir: true,
            data: "hello"
        });

        const full = path.join(root, rel);
        const contents = await fs.readFile(full, 'utf8');
        assert.strictEqual(contents, "hello");
    });

    })