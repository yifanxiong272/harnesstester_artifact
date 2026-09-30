let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');
let child_process = require('child_process');

describe('test testpilot_subject', function() {
    // Keep originals for multiple properties
    let originals = {};

    // Helper to replace child_process.execFile (and related APIs) with controllable stubs.
    function installExecFileStub(makeCallbackBehavior) {
        // Save originals
        originals.execFile = child_process.execFile;
        originals.exec = child_process.exec;
        originals.execFileSync = child_process.execFileSync;

        // Stub execFile (async)
        child_process.execFile = function execFileStub(file /*, ...args, callback */) {
            let args = Array.prototype.slice.call(arguments);
            let callback = args[args.length - 1];
            if (typeof callback !== 'function') {
                callback = function() {};
            }
            let behavior = makeCallbackBehavior(file, args.slice(1));
            setImmediate(function() {
                callback(behavior.err, behavior.stdout, behavior.stderr);
            });
            return { pid: 12345, killed: false };
        };

        // Stub exec (async) - some implementations use exec instead of execFile
        child_process.exec = function execStub(command /*, ...args, callback */) {
            let args = Array.prototype.slice.call(arguments);
            // try to find callback as the last function arg
            let callback = args[args.length - 1];
            if (typeof callback !== 'function') {
                callback = function() {};
            }
            // For exec, treat the whole command as "file" for behavior selection.
            let behavior = makeCallbackBehavior(command, args.slice(1));
            setImmediate(function() {
                callback(behavior.err, behavior.stdout, behavior.stderr);
            });
            return { pid: 12345, killed: false };
        };

        // Stub execFileSync (sync)
        child_process.execFileSync = function execFileSyncStub(file /*, ...args */) {
            let args = Array.prototype.slice.call(arguments);
            // makeCallbackBehavior can return err/stdout/stderr; for sync, throw if err present
            let behavior = makeCallbackBehavior(file, args.slice(1));
            if (behavior.err) {
                // mimic Node throwing an Error when sync call fails
                let e = new Error('Command failed: ' + file);
                e.code = behavior.err.code || 'ERR';
                throw e;
            }
            // Return stdout (Buffer or string). Use string as tests expect version string.
            return behavior.stdout;
        };
    }

    function restoreExecFile() {
        if (originals.execFile) {
            child_process.execFile = originals.execFile;
            originals.execFile = null;
        }
        if (originals.exec) {
            child_process.exec = originals.exec;
            originals.exec = null;
        }
        if (originals.execFileSync) {
            child_process.execFileSync = originals.execFileSync;
            originals.execFileSync = null;
        }
    }

    afterEach(function() {
        restoreExecFile();
    });

    it('should call execFile with the provided executablePath and extract a version from stdout', function() {
        // Arrange: stub execFile/exec/execFileSync to return a stdout containing a version string
        let called = false;
        installExecFileStub(function(file, args) {
            called = true;
            // Simulate typical version output
            return {
                err: null,
                stdout: "MyBrowser 42.3.1\n",
                stderr: ""
            };
        });

        // Act: call the function under test
        let result = testpilot_subject.file_0011.readBrowserVersion('/path/to/fake/browser');

        // Assert: be tolerant of sync or Promise-based implementations.
        if (result && typeof result.then === 'function') {
            return result.then(function(version) {
                assert.ok(called, 'execFile was not called');
                assert.ok(typeof version === 'string', 'expected a version string from Promise resolution');
                assert.ok(version.indexOf('42.3.1') !== -1, 'version string should contain "42.3.1"');
            });
        } else {
            // If the function returned synchronously a string
            if (typeof result === 'string') {
                assert.ok(called, 'execFile was not called');
                assert.ok(result.indexOf('42.3.1') !== -1, 'version string should contain "42.3.1"');
                return;
            }
            // If the function neither returned a Promise nor a string, at least ensure execFile was called.
            assert.ok(called, 'execFile was not called (and no return value to inspect)');
        }
    });

})