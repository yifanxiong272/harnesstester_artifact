let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');
const Module = require('module');

describe('test testpilot_subject', function() {
    // We'll create a temporary node_modules-like folder containing a stub
    // for the import_failover_matches module so the function under test
    // calls our controlled isAuthErrorMessage implementation.
    let tmpModulesDir;
    let oldNodePath;
    let testpilot_subject;

    before(function() {
        // Save and then set NODE_PATH so require() will find our temporary module by bare name.
        oldNodePath = process.env.NODE_PATH || '';

        tmpModulesDir = path.join(process.cwd(), 'test_tmp_node_modules_' + Date.now());
        const stubModuleDir = path.join(tmpModulesDir, 'import_failover_matches');
        fs.mkdirSync(stubModuleDir, { recursive: true });

        // Stub implementation: isAuthErrorMessage returns true only when the message is exactly 'match'.
        const stubCode = 'module.exports = { isAuthErrorMessage: function(msg) { return msg === "match"; } };';
        fs.writeFileSync(path.join(stubModuleDir, 'index.js'), stubCode, 'utf8');

        // Make Node include our temp dir when resolving modules with bare names.
        process.env.NODE_PATH = tmpModulesDir + (oldNodePath ? path.delimiter + oldNodePath : '');
        Module._initPaths();

        // Ensure we load a fresh copy of testpilot_subject (in case tests are re-run in same process)
        try { delete require.cache[require.resolve('testpilot_subject')]; } catch (e) { /* ignore if not cached */ }
        testpilot_subject = require('..');
    });

    after(function() {
        // Restore NODE_PATH and module paths.
        process.env.NODE_PATH = oldNodePath;
        Module._initPaths();

        // Remove the temporary module directory.
        try {
            // fs.rmSync is available in modern Node; fallback to rmdirSync when necessary.
            if (fs.rmSync) {
                fs.rmSync(tmpModulesDir, { recursive: true, force: true });
            } else {
                // recursive removal fallback
                const rimraf = function(dir) {
                    if (!fs.existsSync(dir)) return;
                    for (const entry of fs.readdirSync(dir)) {
                        const cur = path.join(dir, entry);
                        if (fs.lstatSync(cur).isDirectory()) rimraf(cur);
                        else fs.unlinkSync(cur);
                    }
                    fs.rmdirSync(dir);
                };
                rimraf(tmpModulesDir);
            }
        } catch (e) {
            // best-effort cleanup; do not fail the tests just because cleanup failed
        }

        // Clear any cached copy of testpilot_subject to avoid cross-test pollution.
        try { delete require.cache[require.resolve('testpilot_subject')]; } catch (e) { /* ignore */ }
    });

    it('returns false when msg is falsy or stopReason is not "error"', function() {
        const fn = testpilot_subject.file_0001.isAuthAssistantError;
        assert.strictEqual(fn(null), false, 'null msg should return false');
        assert.strictEqual(fn(undefined), false, 'undefined msg should return false');
        assert.strictEqual(fn({}), false, 'missing stopReason should return false');
        assert.strictEqual(fn({ stopReason: 'not_error', errorMessage: 'match' }), false, 'non-error stopReason should return false even if message would match');
    });

    })