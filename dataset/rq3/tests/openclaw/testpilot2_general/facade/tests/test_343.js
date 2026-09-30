let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
let os = require('os');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // keep originals to restore after tests
    const ORIGINAL_ENV = {
        PROGRAMFILES: process.env.PROGRAMFILES,
        'PROGRAMFILES(X86)': process.env['PROGRAMFILES(X86)'],
        LOCALAPPDATA: process.env.LOCALAPPDATA
    };

    // helper to create a fake chrome.exe under a given base dir
    function makeFakeChromeUnder(baseDir) {
        const chromeDir = path.join(baseDir, 'Google', 'Chrome', 'Application');
        fs.mkdirSync(chromeDir, { recursive: true });
        const chromePath = path.join(chromeDir, 'chrome.exe');
        fs.writeFileSync(chromePath, 'fake chrome binary');
        return chromePath;
    }

    // cleanup helper
    function rimrafSync(p) {
        if (!fs.existsSync(p)) return;
        let stat = fs.lstatSync(p);
        if (stat.isDirectory()) {
            for (let entry of fs.readdirSync(p)) {
                rimrafSync(path.join(p, entry));
            }
            fs.rmdirSync(p);
        } else {
            fs.unlinkSync(p);
        }
    }

    afterEach(function() {
        // restore env
        process.env.PROGRAMFILES = ORIGINAL_ENV.PROGRAMFILES;
        process.env['PROGRAMFILES(X86)'] = ORIGINAL_ENV['PROGRAMFILES(X86)'];
        process.env.LOCALAPPDATA = ORIGINAL_ENV.LOCALAPPDATA;
    });

    it('returns falsy when chrome is not present in any expected location', function() {
        // point env vars to empty temp dirs without chrome.exe
        const tmp1 = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-empty1-'));
        const tmp2 = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-empty2-'));
        const tmp3 = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-empty3-'));
        process.env.PROGRAMFILES = tmp1;
        process.env['PROGRAMFILES(X86)'] = tmp2;
        process.env.LOCALAPPDATA = tmp3;

        const result = testpilot_subject.file_0011.findGoogleChromeExecutableWindows();
        // should be falsy (null/undefined/empty) because we didn't create chrome.exe
        assert.ok(!result);

        rimrafSync(tmp1);
        rimrafSync(tmp2);
        rimrafSync(tmp3);
    });
});