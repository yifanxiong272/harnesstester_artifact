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

    it('returns null/undefined (falsy) when no candidate paths exist', function() {
        // make every existsSync call return false
        fs.existsSync = function(p) {
            return false;
        };

        const result = testpilot_subject.file_0011.findChromeExecutableMac();
        assert.ok(!result, 'Expected a falsy return value when no Chrome executables are present');
    });
});