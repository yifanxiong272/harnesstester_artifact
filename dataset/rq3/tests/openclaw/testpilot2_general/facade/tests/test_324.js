let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let fs = require('fs');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    const file = testpilot_subject.file_0011;

    let origExistsSync;
    let origExecSync;
    let origEnv;
    let origPlatformDescriptor;

    beforeEach(function() {
        // save originals so we can restore them
        origExistsSync = fs.existsSync;
        origExecSync = child_process.execSync;
        // copy env
        origEnv = Object.assign({}, process.env);

        // Save the original platform property descriptor (if possible) so we can restore it.
        // This tries to be defensive in case the property is non-configurable in some envs.
        try {
            origPlatformDescriptor = Object.getOwnPropertyDescriptor(process, 'platform');
            Object.defineProperty(process, 'platform', { value: 'win32' });
        } catch (e) {
            // If we cannot redefine platform, continue; tests will still attempt to work.
            origPlatformDescriptor = null;
        }
    });

    afterEach(function() {
        // restore stubs
        fs.existsSync = origExistsSync;
        child_process.execSync = origExecSync;
        // restore env
        process.env = Object.assign({}, origEnv);

        // restore platform descriptor if we changed it
        try {
            if (origPlatformDescriptor) {
                Object.defineProperty(process, 'platform', origPlatformDescriptor);
            }
        } catch (e) {
            // ignore restore error
        }
    });

    it('falls back to PROGRAMFILES chrome.exe path when LOCALAPPDATA is absent', function() {
        // arrange
        delete process.env.LOCALAPPDATA;
        process.env.PROGRAMFILES = 'C:\\Program Files';
        const expectedPath = process.env.PROGRAMFILES + '\\Google\\Chrome\\Application\\chrome.exe';
        const expected = { kind: 'chrome', path: expectedPath };

        fs.existsSync = function(p) {
            return p === expectedPath;
        };

        // act
        const result = file.findChromeExecutableWindows();

        // assert
        assert.deepStrictEqual(result, expected);
    });

    })