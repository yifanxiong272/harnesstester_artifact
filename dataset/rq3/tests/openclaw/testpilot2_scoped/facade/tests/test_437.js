let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const fs = require('fs');
const child_process = require('child_process');

describe('test testpilot_subject', function() {
    // Keep originals to restore after each test
    const origExistsSync = fs.existsSync;
    const origReadFileSync = fs.readFileSync;
    const origExecSync = child_process.execSync;

    afterEach(function() {
        // Restore originals to avoid leaking stubs between tests
        fs.existsSync = origExistsSync;
        fs.readFileSync = origReadFileSync;
        child_process.execSync = origExecSync;
    });

    it('returns false when both filesystem and shell checks fail (command throws)', async function() {
        // Arrange: no completion file and shell command fails/throws
        fs.existsSync = function(path) { return false; };
        child_process.execSync = function(cmd, opts) {
            throw new Error("simulated shell failure");
        };

        // Act
        let result = await testpilot_subject.file_0015.isCompletionInstalled('bash', 'openclaw');

        // Assert
        assert.strictEqual(result, false, 'Expected completion to be reported as not installed when shell check fails');
    });
});