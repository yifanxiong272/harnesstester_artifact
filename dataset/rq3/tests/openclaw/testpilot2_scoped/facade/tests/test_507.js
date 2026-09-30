let os = require('os');
let path = require('path');
let fs = require('fs');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case filesystem ops are slow on CI
    this.timeout(5000);

    // Helper to create a temporary directory for each test
    function makeTempDir(prefix = 'tp-') {
        return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    }

    // Helper to remove a directory tree (synchronous)
    function removeDir(dir) {
        try {
            fs.rmSync(dir, { recursive: true, force: true });
        } catch (e) {
            // best-effort cleanup
        }
    }

    it('must not allow appending to a path that escapes the root using ../ (path traversal)', async function() {
        let root = makeTempDir();
        let outsideFile = path.join(path.dirname(root), 'outside_traversal.txt');
        // Ensure the outside file does not exist before test
        try {
            if (fs.existsSync(outsideFile)) fs.unlinkSync(outsideFile);

            // Attempt to append using a path that tries to escape the root
            // We accept either behavior: the function should throw OR not create the outside file.
            let threw = false;
            try {
                await testpilot_subject.file_0018.appendFileWithinRoot({
                    root: root,
                    path: path.join('..', path.basename(outsideFile)), // '../outside_traversal.txt'
                    data: 'malicious'
                });
            } catch (err) {
                threw = true;
            }

            // After the call, ensure no file was created outside the root.
            let outsideExists = fs.existsSync(outsideFile);
            assert.ok(threw || !outsideExists, 'function must not allow creating files outside the root (either throw or not create the file)');

        } finally {
            // Clean up any accidental outside file and the temp root
            try { if (fs.existsSync(outsideFile)) fs.unlinkSync(outsideFile); } catch (e) {}
            removeDir(root);
        }
    });

    })