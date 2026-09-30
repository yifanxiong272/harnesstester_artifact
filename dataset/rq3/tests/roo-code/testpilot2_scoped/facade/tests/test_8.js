let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Use async tests and some temporary files in OS temp dir.
    const tmpDir = os.tmpdir();
    const createdFiles = [];

    after(function() {
        // Cleanup any files we created.
        for (const f of createdFiles) {
            try { fs.unlinkSync(f); } catch (e) {}
        }
    });

    it('should return an error string when file does not exist', async function() {
        const nonExistentPath = path.join(tmpDir, `no_such_file_${Date.now()}.doesnotexist`);
        // Ensure it truly does not exist
        try { fs.unlinkSync(nonExistentPath); } catch (e) {}
        const res = await testpilot_subject.file_0003.parseSourceCodeDefinitionsForFile(nonExistentPath, null);
        assert.strictEqual(res, "This file does not exist or you do not have permission to access it.");
    });

    })