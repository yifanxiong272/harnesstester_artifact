let mocha = require('mocha');
let assert = require('assert');
let path = require('path');
let fs = require('fs');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals so we can restore them after tests
    const originalExistsSync = fs.existsSync;
    const originalStatSync = fs.statSync;
    const originalAccessSync = fs.accessSync;
    const originalHome = process.env.HOME;

    // Helper to install simple fs stubs for each test case.
    // existsSet is a Set of paths that should be reported as existing.
    function installFsStubs(existsSet) {
        fs.existsSync = function(p) {
            // Normalize for consistency
            let np = path.normalize(p);
            return existsSet.has(np);
        };
        fs.statSync = function(p) {
            // Return an object with isFile method; many implementations just check isFile()
            return { isFile: () => existsSet.has(path.normalize(p)) };
        };
        // Some implementations might call accessSync; make it no-op or throw if missing
        fs.accessSync = function(p /*, mode */) {
            if (!existsSet.has(path.normalize(p))) {
                let err = new Error('ENOENT');
                err.code = 'ENOENT';
                throw err;
            }
            // otherwise no-op (exists)
        };
    }

    afterEach(function() {
        // restore fs methods and HOME env
        fs.existsSync = originalExistsSync;
        fs.statSync = originalStatSync;
        fs.accessSync = originalAccessSync;
        process.env.HOME = originalHome;
    });

    it('should return a falsy value when Chrome cannot be found', function(done) {
        // No paths exist
        installFsStubs(new Set());
        process.env.HOME = '/does/not/matter';

        const found = testpilot_subject.file_0011.findGoogleChromeExecutableMac();
        // The implementation may return null or undefined or empty string; assert it's falsy
        assert.ok(!found, 'Expected a falsy result when Chrome is not present, got: ' + found);
        done();
    });
});