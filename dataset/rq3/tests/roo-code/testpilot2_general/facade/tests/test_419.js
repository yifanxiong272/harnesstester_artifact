let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('testpilot_subject.file_0010.parseSourceCodeDefinitionsForFile', function() {
    // helper to create a unique temp file path
    function tempPath(name) {
        return path.join(os.tmpdir(), `${name}-${Date.now()}-${Math.random().toString(36).slice(2)}`);
    }

    it('returns error message for a non-existent file', async function() {
        const missing = tempPath('no-such-file') + '.txt';
        // ensure the file does not exist
        try { fs.unlinkSync(missing); } catch (e) {}
        const res = await testpilot_subject.file_0010.parseSourceCodeDefinitionsForFile(missing);
        assert.strictEqual(res, "This file does not exist or you do not have permission to access it.");
    });

    })