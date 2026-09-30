let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a temp directory and a fake executable inside it.
    function makeTempWithExecutable(filename, content) {
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-'));
        const fullPath = path.join(tmpDir, filename);
        fs.writeFileSync(fullPath, content || '#!/bin/sh\nexit 0\n', { mode: 0o755 });
        // Ensure executable bit set
        fs.chmodSync(fullPath, 0o755);
        return { tmpDir, fullPath };
    }

    // Save original PATH so tests can restore it
    const originalPATH = process.env.PATH;

    afterEach(function() {
        process.env.PATH = originalPATH;
    });

    it('should return falsy when no chrome-like executables are present in PATH', function(done) {
        // Arrange: point PATH to an empty temporary directory
        const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-empty-'));
        try {
            process.env.PATH = tmpDir;

            // Act
            const result = testpilot_subject.file_0011.findChromeExecutableLinux();

            // Assert: expect a falsy result (null/undefined/empty)
            assert.ok(!result, 'Expected no path to be found when PATH contains no executables');
            done();
        } finally {
            try { fs.rmdirSync(tmpDir); } catch (e) {}
        }
    });
});