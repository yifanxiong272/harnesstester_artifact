let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case filesystem operations are slow on CI
    this.timeout(5000);

    // Helper to create a temporary directory and files
    function makeTempDirWithContents(items) {
        const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'fsservice-test-'));
        for (let it of items) {
            const p = path.join(tmpBase, it);
            if (it.endsWith('/')) {
                fs.mkdirSync(p);
            } else {
                fs.writeFileSync(p, 'content-' + it);
            }
        }
        return tmpBase;
    }

    // Helper to remove directory recursively
    function removeDirRecursive(p) {
        if (fs.existsSync(p)) {
            // Node 12+ has rmSync with recursive; fall back to rmdirSync for older versions
            if (fs.rmSync) {
                fs.rmSync(p, { recursive: true, force: true });
            } else {
                // recursive rmdir (older node)
                (function rimrafSync(r) {
                    if (!fs.existsSync(r)) return;
                    for (const entry of fs.readdirSync(r)) {
                        const full = path.join(r, entry);
                        const st = fs.lstatSync(full);
                        if (st.isDirectory()) rimrafSync(full);
                        else fs.unlinkSync(full);
                    }
                    fs.rmdirSync(r);
                })(p);
            }
        }
    }

    // Acquire the FsService constructor if present
    let FsServiceCtor = undefined;
    if (testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService) {
        FsServiceCtor = testpilot_subject.file_0004.FsService;
    }

    it('FsService.list should exist and be a function', function() {
        assert.ok(FsServiceCtor, 'FsService constructor not found at testpilot_subject.file_0004.FsService');
        assert.strictEqual(typeof FsServiceCtor.prototype.list, 'function', 'list should be a function on the prototype');
    });

    })