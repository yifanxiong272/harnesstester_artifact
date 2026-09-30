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

    it('returns the first candidate path that exists (simulated by making the first existsSync call true)', function() {
        let checked = [];
        let callCount = 0;

        // monkeypatch fs.existsSync: record each checked path; make only the first check return true
        fs.existsSync = function(p) {
            callCount++;
            checked.push(p);
            return callCount === 1;
        };

        const result = testpilot_subject.file_0011.findChromeExecutableMac();

        // The function now returns an object like { kind: 'chrome', path: '...' }.
        // Ensure it returned the expected kind and that the path matches the first existing candidate.
        assert.ok(result && typeof result === 'object', 'Expected result to be an object');
        assert.strictEqual(result.kind, 'chrome', 'Expected returned object to have kind "chrome"');
        assert.strictEqual(result.path, checked[0], 'Expected returned path to be the first existing candidate path');
        // Also ensure at least one candidate was checked
        assert.ok(checked.length >= 1, 'Expected the function to check at least one candidate path');
    });

    })