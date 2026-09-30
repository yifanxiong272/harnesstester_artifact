let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let origExists;

    beforeEach(function() {
        // save original fs.existsSync so tests can safely monkeypatch and restore it
        origExists = fs.existsSync;
    });

    afterEach(function() {
        // restore original implementation after each test
        fs.existsSync = origExists;
    });

    it('returns a later candidate path if earlier candidates are missing (simulated by making the second existsSync call true)', function() {
        let checked = [];
        let callCount = 0;

        // only the second existsSync call returns true
        fs.existsSync = function(p) {
            callCount++;
            checked.push(p);
            return callCount === 2;
        };

        const result = testpilot_subject.file_0011.findChromeExecutableMac();

        // normalize result: some implementations return a plain path string,
        // others return an object like { kind: 'chrome', path: '...' }
        const returnedPath = (result && typeof result === 'object' && 'path' in result) ? result.path : result;

        // If the implementation checks multiple candidate paths, it should return the one we allowed (the second)
        if (checked.length >= 2) {
            assert.strictEqual(returnedPath, checked[1], 'Expected returned path to be the second existing candidate path');
        } else {
            // If the implementation only checks one path, then returnedPath should be falsy because we only made second call true
            assert.ok(!returnedPath, 'Expected no path found when only second simulated candidate exists but only one candidate was checked');
        }
    });

    })