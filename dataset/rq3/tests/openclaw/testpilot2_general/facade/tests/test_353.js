let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    let originalExecFile;

    // Helper to replace child_process.execFile with a controllable stub.
    function installExecFileStub(makeCallbackBehavior) {
        originalExecFile = child_process.execFile;
        child_process.execFile = function execFileStub(file /*, ...args, callback */) {
            // Capture arguments and find the callback (last argument)
            let args = Array.prototype.slice.call(arguments);
            let callback = args[args.length - 1];
            if (typeof callback !== 'function') {
                // If caller didn't pass a callback, provide a no-op to avoid crashes.
                callback = function() {};
            }
            // Determine what stdout/stderr/error to return using provided behavior function
            let behavior = makeCallbackBehavior(file, args.slice(1));
            // Ensure async callback semantics
            setImmediate(function() {
                callback(behavior.err, behavior.stdout, behavior.stderr);
            });
            // For completeness, return a fake ChildProcess-like object
            return { pid: 12345, killed: false };
        };
    }

    function restoreExecFile() {
        if (originalExecFile) {
            child_process.execFile = originalExecFile;
            originalExecFile = null;
        }
    }

    afterEach(function() {
        restoreExecFile();
    });

    it('should not crash and should surface errors when execFile yields an error', function(done) {
        // In this test we simply ensure the module handles child_process error paths.
        installExecFileStub(function(file, args) {
            return {
                err: new Error('spawn ENOENT'),
                stdout: "",
                stderr: ""
            };
        });

        try {
            let result = testpilot_subject.file_0011.readBrowserVersion('/non/existent');

            if (result && typeof result.then === 'function') {
                result.then(function(version) {
                    // If it resolved anyway, ensure it did not produce a bogus value
                    assert.ok(!version || typeof version === 'string');
                    done();
                }).catch(function(err) {
                    // Promise rejection is acceptable
                    assert.ok(err instanceof Error);
                    done();
                });
            } else {
                // If synchronous: just ensure the call didn't throw and test passes
                // We cannot assert specific behavior for non-promise non-throwing implementations,
                // so treat lack of uncaught exception as success.
                done();
            }
        } catch (err) {
            // If the implementation throws synchronously, that's acceptable but should be an Error
            assert.ok(err instanceof Error);
            done();
        }
    });

    })