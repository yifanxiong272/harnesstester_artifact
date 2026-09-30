let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let path = require('path');

describe('test testpilot_subject', function() {
    // Prepare a fake import_failover_matches module so the function under test
    // will call our predictable isAuthErrorMessage implementation.
    const fakeModuleDir = path.join(process.cwd(), 'node_modules', 'import_failover_matches');
    const fakeModuleFile = path.join(fakeModuleDir, 'index.js');

    // Create fake module before requiring the module under test.
    before(function() {
        fs.mkdirSync(fakeModuleDir, { recursive: true });
        // Export an isAuthErrorMessage that returns true only when the message contains 'MAGIC_AUTH'
        const content = `
            module.exports = {
                isAuthErrorMessage: function(msg) {
                    // normalize to string in case undefined/null is passed
                    msg = String(msg || "");
                    return msg.indexOf("MAGIC_AUTH") !== -1;
                }
            };
        `;
        fs.writeFileSync(fakeModuleFile, content, 'utf8');

        // Clear any cached modules so the fresh fake module is picked up
        try { delete require.cache[require.resolve('import_failover_matches')]; } catch (e) {}
    });

    // Clean up fake module and caches after tests run.
    after(function() {
        try {
            // Remove the fake module file and directory
            fs.rmSync(fakeModuleDir, { recursive: true, force: true });
        } catch (e) {
            // ignore cleanup errors
        }
        // Clear require caches for both the fake module and the module under test
        try { delete require.cache[require.resolve('import_failover_matches')]; } catch (e) {}
        try { delete require.cache[require.resolve('testpilot_subject')]; } catch (e) {}
    });

    // Now require the module under test (after the fake dependency exists)
    let testpilot_subject = require('..');

    it('returns false when msg is falsy (null/undefined)', function() {
        const fn = testpilot_subject.file_0001.isAuthAssistantError;
        assert.strictEqual(typeof fn, 'function', 'isAuthAssistantError should be a function');
        assert.strictEqual(fn(null), false);
        assert.strictEqual(fn(undefined), false);
    });

    })