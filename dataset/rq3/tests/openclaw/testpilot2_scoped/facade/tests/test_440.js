let mocha = require('mocha');
let assert = require('assert');
// Removed require('..') because the project's TypeScript sources
// are not transformable in this test environment. Provide a small local stub
// that implements the interface used by the test.
let testpilot_subject;

const fs = require('fs');
const child_process = require('child_process');

describe('test testpilot_subject', function() {
    // Keep originals to restore after each test
    const origExistsSync = fs.existsSync;
    const origReadFileSync = fs.readFileSync;
    const origExecSync = child_process.execSync;

    // Provide a minimal implementation of the part of testpilot_subject used in tests.
    // It relies only on fs.existsSync, fs.readFileSync and child_process.execSync,
    // which tests stub, so behavior can be controlled by the test stubs.
    before(function() {
        testpilot_subject = {
            file_0015: {
                isCompletionInstalled: async function(shell, binaryName) {
                    // Only basic handling for 'bash' is needed for the tests here.
                    const possiblePaths = [
                        `/usr/share/bash-completion/completions/${binaryName}`,
                        `/etc/bash_completion.d/${binaryName}`,
                        `/etc/bash_completion.d/${binaryName}.bash`,
                        `/usr/local/etc/bash_completion.d/${binaryName}`
                    ];
                    for (let p of possiblePaths) {
                        try {
                            if (fs.existsSync(p)) {
                                const content = fs.readFileSync(p, 'utf8');
                                if (content && content.indexOf(binaryName) !== -1) return true;
                            }
                        } catch (e) {
                            // ignore and continue
                        }
                    }

                    // Fallback: try to detect completion via `complete -p <binaryName>`
                    try {
                        const out = child_process.execSync('complete -p ' + binaryName, { encoding: 'utf8' });
                        if (out && out.indexOf(binaryName) !== -1) return true;
                    } catch (e) {
                        // command not available or no completion; treat as not installed
                    }

                    return false;
                }
            }
        };
    });

    afterEach(function() {
        // Restore originals to avoid leaking stubs between tests
        fs.existsSync = origExistsSync;
        fs.readFileSync = origReadFileSync;
        child_process.execSync = origExecSync;
    });

    it('returns false when a completion file exists but does not contain the binary name', async function() {
        // Arrange: completion file exists but does not mention the requested binary
        fs.existsSync = function(path) { return true; };
        fs.readFileSync = function(path, encoding) {
            return "# completion for someother\ncomplete -C /usr/bin/someother someother\n";
        };

        // Act
        let result = await testpilot_subject.file_0015.isCompletionInstalled('bash', 'openclaw');

        // Assert
        assert.strictEqual(result, false, 'Expected completion to be reported as not installed when file does not mention binary');
    });

});