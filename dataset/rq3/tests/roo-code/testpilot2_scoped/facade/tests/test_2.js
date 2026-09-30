let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case filesystem operations are slow on CI
    this.timeout(5000);

    it('loadRequiredLanguageParsers returns a Promise and resolves for an existing (empty) source directory', async function() {
        // create a temporary directory to act as sourceDirectory
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'loadpar-'));
        try {
            // Call function with an empty filesToParse array and an existing directory.
            // Since the function is documented as async, it should return a Promise that resolves.
            const result = await testpilot_subject.file_0002.loadRequiredLanguageParsers([], tmpDir);
            // Basic sanity checks: it should resolve (no exception) and return an object (not null).
            assert.strictEqual(typeof result, 'object', 'expected result to be an object');
            assert.notStrictEqual(result, null, 'expected result not to be null');
        } finally {
            // cleanup
            try { fs.rmdirSync(tmpDir); } catch (e) { /* ignore cleanup errors */ }
        }
    });

    })