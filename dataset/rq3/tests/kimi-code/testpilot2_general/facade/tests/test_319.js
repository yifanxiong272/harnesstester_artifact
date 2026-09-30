let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to create a FsService-like instance whose prototype is the real FsService prototype
    function makeFsServiceWithCwd(cwd) {
        // Create an object with FsService prototype so resolveDownload can run as instance method
        const svc = Object.create(testpilot_subject.file_0004.FsService.prototype);
        // sessions.get(sessionId) is awaited by resolveDownload, so we provide a simple function/object that returns the session
        svc.sessions = {
            get: async (sessionId) => {
                return { metadata: { cwd: cwd } };
            }
        };
        return svc;
    }

    // create temp dir for tests and remove after
    let tmpRoot;
    before(function() {
        tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'fsservice-test-'));
    });
    after(function() {
        if (tmpRoot && fs.existsSync(tmpRoot)) {
            // recursive remove
            try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch (e) { /* ignore */ }
        }
    });

    it('resolveDownload should return metadata for a plain text file', async function() {
        const cwd = path.join(tmpRoot, 'textfile-cwd');
        fs.mkdirSync(cwd);
        const filename = 'hello.txt';
        const filePath = path.join(cwd, filename);
        const contents = 'hello world\n';
        fs.writeFileSync(filePath, contents, 'utf8');

        const svc = makeFsServiceWithCwd(cwd);
        const result = await svc.resolveDownload('session-1', filename);

        // basic assertions about returned shape and values
        assert.strictEqual(result.absolute, filePath, 'absolute path must match the created file');
        // relative may be returned in slightly different forms, but must end with our filename
        assert.ok(result.relative.endsWith(filename), 'relative must end with the filename');
        assert.strictEqual(result.size, contents.length);
        assert.strictEqual(typeof result.etag, 'string');
        assert.ok(result.etag.length > 0);
        assert.strictEqual(typeof result.mime, 'string');
        assert.ok(result.mime.startsWith('text/'), 'expected a text mime type for .txt file');
        assert.ok(result.modifiedAt instanceof Date);
        // check modifiedAt roughly matches actual mtime
        const st = fs.statSync(filePath);
        assert.ok(Math.abs(result.modifiedAt.getTime() - st.mtimeMs) < 2000, 'modifiedAt should be close to file mtime');
    });

    })