let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

let fs = require('fs');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    // Backups for original functions so we can restore them after each test
    let origExistsSync = fs.existsSync;
    let origAccessSync = fs.accessSync;
    let origStatSync = fs.statSync;
    let origExecSync = child_process.execSync;
    let origSpawnSync = child_process.spawnSync;

    // Helper to create stubs that simulate which files exist and which commands return something.
    function setupStubs(options) {
        // options.exists: Set or array of paths that should be treated as existing
        // options.whichPath: value that 'which' should return (string) or null/undefined to simulate not found
        let allowed = new Set(Array.isArray(options.exists) ? options.exists : (options.exists ? [options.exists] : []));

        fs.existsSync = function(p) {
            // normalize a bit to avoid surprises from small differences
            if (allowed.has(p)) return true;
            return false;
        };

        fs.accessSync = function(p, mode) {
            if (allowed.has(p)) return; // success
            let err = new Error("ENOENT");
            err.code = 'ENOENT';
            throw err;
        };

        // Some implementations may call statSync; give a simple stub that returns an object
        fs.statSync = function(p) {
            if (allowed.has(p)) {
                return { isFile: () => true, isDirectory: () => false };
            }
            let err = new Error("ENOENT");
            err.code = 'ENOENT';
            throw err;
        };

        child_process.execSync = function(cmd, opts) {
            // Emulate `which google-chrome` style calls
            // Return a Buffer or string (both acceptable for execSync)
            if (typeof cmd === 'string' && cmd.indexOf('which') !== -1) {
                if (options.whichPath) {
                    return Buffer.from(options.whichPath + '\n');
                } else {
                    // simulate 'which' not finding anything: return empty Buffer or throw
                    // Many implementations return empty string; we'll return empty Buffer.
                    return Buffer.from('');
                }
            }

            // Default fallback: throw so tests will notice unexpected command usage
            let err = new Error("Unexpected execSync call: " + cmd);
            throw err;
        };

        // Some implementations may use spawnSync; emulate minimal behavior
        child_process.spawnSync = function(cmd, args, opts) {
            if (cmd === 'which' && args && args[0]) {
                if (options.whichPath) {
                    return { status: 0, stdout: Buffer.from(options.whichPath + '\n'), stderr: Buffer.from('') };
                } else {
                    return { status: 1, stdout: Buffer.from(''), stderr: Buffer.from('') };
                }
            }
            let err = new Error("Unexpected spawnSync call: " + cmd + " " + JSON.stringify(args));
            throw err;
        };
    }

    function restoreStubs() {
        fs.existsSync = origExistsSync;
        fs.accessSync = origAccessSync;
        fs.statSync = origStatSync;
        child_process.execSync = origExecSync;
        child_process.spawnSync = origSpawnSync;
    }

    afterEach(function() {
        restoreStubs();
    });

    it('should return falsy when nothing is found', function() {
        // Arrange: nothing exists and which finds nothing
        setupStubs({ exists: [], whichPath: null });

        // Act
        let result = testpilot_subject.file_0011.findGoogleChromeExecutableLinux();

        // Assert: expect a falsy result (null/undefined/empty string are all acceptable as "not found")
        assert.ok(!result, 'expected falsy result when no chrome executable is present');
    });
});