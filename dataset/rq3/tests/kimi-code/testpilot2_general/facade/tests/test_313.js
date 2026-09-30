let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let fsp = fs.promises;
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case the environment is slow
    this.timeout(5000);

    // Helper to create a disposable temp directory for each test
    async function makeTempDir(prefix = 'fs-test-') {
        const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), prefix));
        return tmp;
    }

    it('test testpilot_subject.file_0004.FsService.prototype.mkdir - creates nested dir with recursive=true', async function() {
        const cwd = await makeTempDir();
        const sessionId = 's1';
        // Construct a minimal service instance that has the prototype method
        const svc = Object.create(testpilot_subject.file_0004.FsService.prototype);
        // sessions.get is awaited in the implementation, so make it async
        svc.sessions = {
            get: async (id) => {
                assert.strictEqual(id, sessionId);
                return { metadata: { cwd } };
            }
        };

        const req = { path: 'a/b/c', recursive: true };
        let result;
        try {
            result = await svc.mkdir(sessionId, req);

            // The directory should exist on disk
            const createdAbs = path.join(cwd, 'a', 'b', 'c');
            const st = await fsp.stat(createdAbs);
            assert.ok(st.isDirectory(), 'expected created path to be a directory');

            // The method should return an object (buildFsEntryFromStat result)
            assert.ok(result && typeof result === 'object', 'expected a result object from mkdir');
            // If the returned object contains a name or basename property, it should match
            if ('name' in result) {
                assert.strictEqual(result.name, path.basename(createdAbs));
            }
            if ('relative' in result) {
                // relative may be 'a/b/c' or similar
                assert.ok(result.relative.endsWith(path.join('a','b','c')) || result.relative === path.posix.join('a','b','c'));
            }
        } finally {
            // cleanup created tree
            await fsp.rm(cwd, { recursive: true, force: true });
        }
    });

    })