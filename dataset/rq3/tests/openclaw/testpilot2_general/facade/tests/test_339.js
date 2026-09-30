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

    it('should find Chrome in /Applications when it exists there', function(done) {
        // Typical macOS application executable path
        const appPath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
        const existsSet = new Set([path.normalize(appPath)]);
        installFsStubs(existsSet);

        // Ensure HOME is something deterministic but irrelevant for this test
        process.env.HOME = '/some/fake/home';

        const found = testpilot_subject.file_0011.findGoogleChromeExecutableMac();
        // Adjusted to match the actual return shape ({ kind: 'chrome', path: '...' })
        assert.deepStrictEqual(found, { kind: 'chrome', path: path.normalize(appPath) });
        done();
    });

    })