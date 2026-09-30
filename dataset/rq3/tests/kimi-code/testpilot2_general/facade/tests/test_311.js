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

    it('test testpilot_subject.file_0004.FsService.prototype.mkdir - throws FsAlreadyExistsError when target exists and recursive=false', async function() {
        const cwd = await makeTempDir();
        const sessionId = 's2';
        const svc = Object.create(testpilot_subject.file_0004.FsService.prototype);
        svc.sessions = {
            get: async (id) => ({ metadata: { cwd } })
        };

        const target = path.join(cwd, 'existsDir');
        await fsp.mkdir(target, { recursive: true });

        const req = { path: 'existsDir', recursive: false };
        try {
            await svc.mkdir(sessionId, req);
            // If no error thrown, fail the test
            assert.fail('Expected mkdir to throw when directory already exists and recursive=false');
        } catch (err) {
            // Expect an FsAlreadyExistsError; check constructor name to avoid relying on internal module identity
            assert.ok(err && err.constructor && err.constructor.name === 'FsAlreadyExistsError',
                'Expected error.constructor.name to be FsAlreadyExistsError, got: ' + (err && err.constructor && err.constructor.name));
        } finally {
            await fsp.rm(cwd, { recursive: true, force: true });
        }
    });

    })