let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // The module under test (expected)
    const mod = testpilot_subject.file_0015;
    if (!mod || typeof mod.usesSlowDynamicCompletion !== 'function') {
        // If the subject isn't available as expected, fail early so tests are clear.
        throw new Error('testpilot_subject.file_0015.usesSlowDynamicCompletion not found');
    }

    // Helpers to create temporary files
    function makeTempDir() {
        const base = fs.mkdtempSync(path.join(os.tmpdir(), 'tp-test-'));
        return base;
    }
    function writeFile(p, content) {
        fs.writeFileSync(p, content, 'utf8');
    }
    function removeFileIfExists(p) {
        try { fs.unlinkSync(p); } catch (e) {}
    }
    function removeDirIfExists(d) {
        try { fs.rmdirSync(d); } catch (e) {}
    }

    // We'll attempt to monkeypatch exported helpers if present on the module so the tests are self-contained.
    // Save originals to restore after each test.
    let originals = {};

    function backup(prop) {
        if (prop in mod) {
            originals[prop] = mod[prop];
        } else {
            originals[prop] = undefined;
        }
    }
    function restore(prop) {
        if (originals[prop] === undefined) {
            try { delete mod[prop]; } catch (e) {}
        } else {
            mod[prop] = originals[prop];
        }
    }

    afterEach(function() {
        // Restore any patched properties
        for (const k of Object.keys(originals)) {
            restore(k);
        }
        originals = {};
    });

    it('returns false if profile does not exist', async function() {
        // Patch getShellProfilePath to point to a non-existent file
        backup('getShellProfilePath');
        mod.getShellProfilePath = () => path.join(os.tmpdir(), 'non-existent-profile-' + Date.now());

        // Call the function; it should return false because the profile file doesn't exist.
        const result = await mod.usesSlowDynamicCompletion('bash', 'openclaw');
        assert.strictEqual(result, false);
    });

    })