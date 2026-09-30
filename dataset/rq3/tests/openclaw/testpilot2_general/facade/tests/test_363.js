let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0011.resolveBrowserExecutableForPlatform;

    it('returns a custom kind object when resolved.executablePath exists', function() {
        // create a temporary file to guarantee existence
        const tmpPath = path.join(os.tmpdir(), `tp_test_${Date.now()}_${Math.random()}.bin`);
        fs.writeFileSync(tmpPath, ''); // create the file

        try {
            const result = fn({ executablePath: tmpPath }, 'linux');
            assert.deepStrictEqual(result, { kind: "custom", path: tmpPath });
        } finally {
            // cleanup
            try { fs.unlinkSync(tmpPath); } catch (e) { /* ignore */ }
        }
    });

    })