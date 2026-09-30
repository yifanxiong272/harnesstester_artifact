let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let fs = require('fs');
let os = require('os');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // make tests a little more tolerant in case filesystem operations are a bit slow
    this.timeout(5000);

    const fsp = fs.promises;
    let tmpDir = null;

    beforeEach(async function() {
        // create a fresh temporary directory for each test
        tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-'));
    });

    afterEach(async function() {
        // remove the temporary directory and everything we created in it
        if (tmpDir && fs.existsSync(tmpDir)) {
            // Node v12+ supports fs.promises.rm; fall back to rmdir for older versions
            if (fsp.rm) {
                await fsp.rm(tmpDir, { recursive: true, force: true });
            } else {
                await fsp.rmdir(tmpDir, { recursive: true });
            }
        }
        tmpDir = null;
    });

    it('loadRequiredLanguageParsers resolves correctly for an empty filesToParse array', async function() {
        // No files created; empty list should be handled without throwing
        let result = await testpilot_subject.file_0008.loadRequiredLanguageParsers([], tmpDir);

        assert.ok(result !== undefined && result !== null, 'Expected a non-null/undefined result for empty input');
    });

    })