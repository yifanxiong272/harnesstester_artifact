let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Backup any existing global.execText to avoid interfering with other tests/process
    let originalExecText;
    beforeEach(function() {
        originalExecText = global.execText;
    });
    afterEach(function() {
        global.execText = originalExecText;
    });

    it('returns null when execText returns null', function() {
        // execText should be called but return null -> readBrowserVersion should return null
        global.execText = function(executablePath, args, timeout) {
            // verify args are what the function is supposed to call with
            assert.strictEqual(args[0], "--version");
            assert.strictEqual(timeout, 2000);
            return null;
        };

        let result = testpilot_subject.file_0011.readBrowserVersion('/fake/path/to/browser');
        assert.strictEqual(result, null);
    });

    })