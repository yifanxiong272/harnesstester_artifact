let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // shorthand to the function under test
    const isPathInIgnoredDirectory = testpilot_subject.file_0025.isPathInIgnoredDirectory;
    // import_constants may not exist on the subject, so declare and initialize in beforeEach
    let import_constants;

    beforeEach(function() {
        // ensure import_constants exists on the subject and keep a local reference
        import_constants = testpilot_subject.import_constants = testpilot_subject.import_constants || {};
        // reset DIRS_TO_IGNORE to a known default before each test
        import_constants.DIRS_TO_IGNORE = [];
    });

    it('detects specified directory names (handles backslashes and normalization)', function() {
        import_constants.DIRS_TO_IGNORE = ['node_modules'];
        // Windows-style backslashes should be normalized and detected
        assert.strictEqual(isPathInIgnoredDirectory('C:\\project\\node_modules\\pkg\\index.js'), true);
        // Unix-style path should also be detected
        assert.strictEqual(isPathInIgnoredDirectory('/home/user/project/node_modules/some-module'), true);
    });

})