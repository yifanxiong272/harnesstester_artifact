let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs');
const fsp = fs.promises;
const os = require('os');
const path = require('path');

describe('test testpilot_subject', function() {
    // Increase timeout for file ops on slow CI
    this.timeout(5000);

    let tempRoot;
    let svc;

    // Helper to create new FsService instance with a sessions.get that returns the temporary cwd
    function makeServiceWithCwd(cwd) {
        const Inst = testpilot_subject.file_0004.FsService;
        const svcInstance = new Inst();
        // override sessions to a minimal mock returning the cwd
        svcInstance.sessions = {
            get: async (_sessionId) => {
                return { metadata: { cwd } };
            }
        };
        return svcInstance;
    }

    // create fresh temp dir before each test and remove after
    beforeEach(async () => {
        tempRoot = await fsp.mkdtemp(path.join(os.tmpdir(), 'fsservice-test-'));
        svc = makeServiceWithCwd(tempRoot);
    });

    afterEach(async () => {
        // remove recursively, ignore errors
        try {
            await fsp.rm(tempRoot, { recursive: true, force: true });
        } catch (_) {}
    });

    it('creates a new directory and returns an entry with the correct name', async () => {
        const req = { path: 'newdir', recursive: false };
        const entry = await svc.mkdir('sess1', req);
        // The returned entry should include the name (basename)
        assert.strictEqual(entry.name, 'newdir');

        const stat = await fsp.stat(path.join(tempRoot, 'newdir'));
        assert.ok(stat.isDirectory(), 'newdir should be a directory on disk');
    });

    })