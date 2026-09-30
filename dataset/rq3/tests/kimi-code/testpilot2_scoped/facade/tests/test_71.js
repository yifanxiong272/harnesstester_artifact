let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to create a temporary directory for cwd
    function makeTempDir() {
        const tmpBase = os.tmpdir();
        const prefix = 'fswatcher-test-';
        return fs.mkdtempSync(path.join(tmpBase, prefix));
    }

    // helper to remove temp directory (best-effort)
    function removeDir(dir) {
        try {
            if (fs.rmSync) { // Node >=14.14
                fs.rmSync(dir, { recursive: true, force: true });
            } else {
                // fallback
                fs.rmdirSync(dir, { recursive: true });
            }
        } catch (e) {
            // ignore cleanup errors in tests
        }
    }

    // generic recursive search: check whether an object (or nested) contains a string value
    function containsStringValue(obj, expected) {
        const seen = new Set();
        function search(x) {
            if (!x || (typeof x !== 'object' && typeof x !== 'string')) return false;
            if (typeof x === 'string') return x === expected;
            if (seen.has(x)) return false;
            seen.add(x);
            for (const k of Object.keys(x)) {
                try {
                    const v = x[k];
                    if (typeof v === 'string' && v === expected) return true;
                    if (typeof v === 'object' && search(v)) return true;
                } catch (e) {
                    // ignore getters that throw
                }
            }
            return false;
        }
        return search(obj);
    }

    it('FsWatcherService should expose createSessionEntry as a function', function() {
        assert.ok(testpilot_subject, 'module "testpilot_subject" should be present');
        const FsWatcherService = testpilot_subject.file_0001 && testpilot_subject.file_0001.FsWatcherService;
        assert.ok(FsWatcherService, 'FsWatcherService constructor should exist at file_0001.FsWatcherService');
        assert.equal(typeof FsWatcherService.prototype.createSessionEntry, 'function',
            'createSessionEntry should be a function on the prototype');
    });

    })