let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let path = require('path');
let fs = require('fs');
let os = require('os');

describe('test testpilot_subject', function() {
    // Backup originals so we can restore them after each test
    let origExistsSync, origStatSync, origAccessSync, origHomedir;

    beforeEach(function() {
        origExistsSync = fs.existsSync;
        origStatSync = fs.statSync;
        origAccessSync = fs.accessSync;
        origHomedir = os.homedir;
    });

    afterEach(function() {
        // Restore originals
        fs.existsSync = origExistsSync;
        fs.statSync = origStatSync;
        fs.accessSync = origAccessSync;
        os.homedir = origHomedir;
    });

    // Helper to stub fs checks consistently based on a predicate function
    function stubFsForPredicate(predicate) {
        fs.existsSync = function(p) {
            return !!predicate(p);
        };
        fs.accessSync = function(p) {
            if (!predicate(p)) throw new Error('ENOENT');
            return undefined;
        };
        fs.statSync = function(p) {
            if (!predicate(p)) throw new Error('ENOENT');
            return { isFile: () => true };
        };
    }

    it('returns the first absolute path when that candidate exists', function() {
        // Ensure homedir is stable and known
        os.homedir = () => '/Users/fake';

        const absoluteFirst = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
        // Only the absolute first path "exists"
        stubFsForPredicate(p => p === absoluteFirst);

        const result = testpilot_subject.file_0011.findGoogleChromeExecutableMac();
        // The function returns an object with kind and path, so assert accordingly
        assert.deepStrictEqual(result, { kind: 'chrome', path: absoluteFirst });
    });

    })