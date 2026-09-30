let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // shorthand to the function under test
    const isPathInIgnoredDirectory = testpilot_subject.file_0025.isPathInIgnoredDirectory;
    // ensure import_constants exists on the subject (create it if missing)
    let import_constants = testpilot_subject.import_constants || (testpilot_subject.import_constants = {});

    beforeEach(function() {
        // reset DIRS_TO_IGNORE to a known default before each test
        import_constants.DIRS_TO_IGNORE = [];
    });

    it('does not treat the single dot "." as an ignored directory even when ".*" is present', function() {
        import_constants.DIRS_TO_IGNORE = ['.*'];
        // './file' contains a '.' segment which should NOT be considered an ignored directory
        assert.strictEqual(isPathInIgnoredDirectory('./file'), false);
        // '/./file' includes an explicit '.' segment between slashes; still should be false
        assert.strictEqual(isPathInIgnoredDirectory('/./file'), false);
    });

});