let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0011;
    let origMac, origLinux, origWin;

    beforeEach(function() {
        // Save originals so we can restore them after each test
        origMac = subject.findGoogleChromeExecutableMac;
        origLinux = subject.findGoogleChromeExecutableLinux;
        origWin = subject.findGoogleChromeExecutableWindows;
    });

    afterEach(function() {
        // Restore originals to avoid side effects between tests
        subject.findGoogleChromeExecutableMac = origMac;
        subject.findGoogleChromeExecutableLinux = origLinux;
        subject.findGoogleChromeExecutableWindows = origWin;
    });

    it('returns the Mac helper result when platform is "darwin"', function() {
        // Arrange: stub the Mac helper
        subject.findGoogleChromeExecutableMac = function() {
            return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
        };

        // Act
        const result = subject.resolveGoogleChromeExecutableForPlatform('darwin');

        // Assert
        assert.deepStrictEqual(result, {
            kind: 'chrome',
            path: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        });
    });

});