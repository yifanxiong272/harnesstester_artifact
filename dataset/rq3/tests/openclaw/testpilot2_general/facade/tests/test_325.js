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

    it('returns LOCALAPPDATA chrome.exe path when that file exists', function() {
        // arrange
        process.env.LOCALAPPDATA = 'C:\\Users\\Alice\\AppData\\Local';
        // expected path the implementation is likely to check
        const expected = process.env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe';

        // stub fs.existsSync to only return true for the expected path
        fs.existsSync = function(p) {
            return p === expected;
        };

        // act
        const result = file.findChromeExecutableWindows();

        // assert
        // The implementation returns an object with kind and path properties.
        assert.deepStrictEqual(result, { kind: 'chrome', path: expected });
    });

    })