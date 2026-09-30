let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs').promises;
const path = require('path');
const os = require('os');

describe('test testpilot_subject.file_0018.copyFileWithinRoot', function() {
    // Helper to create a temporary directory for each test
    async function makeTempRoot(prefix = 'tp-copy-') {
        return fs.mkdtemp(path.join(os.tmpdir(), prefix));
    }

    // Helper to remove a directory tree (best-effort)
    async function removeIfExists(p) {
        try {
            // fs.rm with recursive is supported on modern Node.js versions
            if (fs.rm) {
                await fs.rm(p, { recursive: true, force: true });
            } else {
                // fallback for older Node versions
                await fs.rmdir(p, { recursive: true });
            }
        } catch (e) {
            // ignore cleanup errors
        }
    }

    it('rejects when attempting to copy a source file that is outside the provided root', async function() {
        const root = await makeTempRoot();
        const outsideDir = await makeTempRoot('tp-outside-');
        try {
            const outsideFile = path.join(outsideDir, 'outside.txt');
            await fs.writeFile(outsideFile, 'do not allow', 'utf8');

            // Attempt to copy using an absolute path that is outside of the root.
            // The function should not allow copying from outside the root and should reject.
            await assert.rejects(
                async () => {
                    await testpilot_subject.file_0018.copyFileWithinRoot({
                        root: root,
                        src: outsideFile, // absolute path outside root
                        dst: 'somewhere.txt'
                    });
                },
                Error
            );
        } finally {
            await removeIfExists(root);
            await removeIfExists(outsideDir);
        }
    });

    })