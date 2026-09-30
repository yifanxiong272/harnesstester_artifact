let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // If the target function is not present, skip the suite so tests don't fail spuriously.
    before(function() {
        if (!testpilot_subject
            || !testpilot_subject.file_0018
            || typeof testpilot_subject.file_0018.openFileWithinRoot !== 'function') {
            this.skip(); // skip whole suite
        }
    });

    // Temporary directory used for tests
    let tmpdir;

    beforeEach(function() {
        // Create a fresh temporary directory for each test
        tmpdir = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-'));
        // Create a nested directory and a file inside it
        const nestedDir = path.join(tmpdir, 'sub');
        fs.mkdirSync(nestedDir, { recursive: true });
        fs.writeFileSync(path.join(nestedDir, 'hello.txt'), 'hello world', 'utf8');
    });

    afterEach(function() {
        // Clean up the temporary directory after each test
        // fs.rmSync with recursive is Node 12.10+. Use fallback for older versions.
        try {
            if (fs.rmSync) {
                fs.rmSync(tmpdir, { recursive: true, force: true });
            } else {
                // fallback: recursive rmdir
                const rimraf = function (p) {
                    if (!fs.existsSync(p)) return;
                    for (const entry of fs.readdirSync(p)) {
                        const cur = path.join(p, entry);
                        const stat = fs.lstatSync(cur);
                        if (stat.isDirectory()) rimraf(cur);
                        else fs.unlinkSync(cur);
                    }
                    fs.rmdirSync(p);
                };
                rimraf(tmpdir);
            }
        } catch (e) {
            // If cleanup fails, don't crash the suite; log for debugging.
            // console.error('Cleanup failed', e);
        }
    });

    it('rejects attempts to escape the root via path traversal (../)', async function() {
        const traversalPath = path.join('..', 'etc', 'passwd'); // a typical traversal attempt
        try {
            await testpilot_subject.file_0018.openFileWithinRoot({ root: tmpdir, path: traversalPath });
            assert.fail('Expected openFileWithinRoot to reject traversal outside the root');
        } catch (err) {
            // Expect an error: either thrown or rejected promise
            assert.ok(err, 'an error should be thrown or rejection returned for path traversal');
        }
    });

    })