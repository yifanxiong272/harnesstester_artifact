let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Locate the function under test
    let idFn;
    before(function() {
        // Access the function; if the path does not exist this will throw and the suite will fail early.
        idFn = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[1].id;
    });

    it('should exist and be a function', function() {
        assert.ok(idFn, 'expected id function to be present');
        assert.strictEqual(typeof idFn, 'function');
    });

    })