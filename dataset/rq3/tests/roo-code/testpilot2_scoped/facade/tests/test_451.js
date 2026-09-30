let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // shorthand to the function under test
    const isPathInIgnoredDirectory = testpilot_subject.file_0025.isPathInIgnoredDirectory;

    // ensure import_constants exists on the module under test so the test can modify it
    const import_constants = testpilot_subject.import_constants || (testpilot_subject.import_constants = { DIRS_TO_IGNORE: [] });

    beforeEach(function() {
        // reset DIRS_TO_IGNORE to a known default before each test
        import_constants.DIRS_TO_IGNORE = [];
    });

    it('returns true for hidden directories when ".*" is in DIRS_TO_IGNORE', function() {
        import_constants.DIRS_TO_IGNORE = ['.*'];
        // leading slash, hidden directory as a path segment
        assert.strictEqual(isPathInIgnoredDirectory('/foo/.git/objects/abc'), true);
        // relative path starting with a hidden directory
        assert.strictEqual(isPathInIgnoredDirectory('.hidden/file'), true);
        // hidden directory not at start
        assert.strictEqual(isPathInIgnoredDirectory('src/.cache/tmp'), true);
    });

});