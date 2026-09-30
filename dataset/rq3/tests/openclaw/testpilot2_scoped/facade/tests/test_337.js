let mocha = require('mocha');
let assert = require('assert');

// ensure we require the subject after we have access to child_process (we will monkeypatch it at runtime)
let testpilot_subject = require('..');

let child_process = require('child_process');
let stream = require('stream');
let EventEmitter = require('events').EventEmitter;

describe('test testpilot_subject', function() {
    let origExecFile, origSpawn;

    beforeEach(function() {
        // save originals
        origExecFile = child_process.execFile;
        origSpawn = child_process.spawn;
    });

    afterEach(function() {
        // restore originals
        child_process.execFile = origExecFile;
        child_process.spawn = origSpawn;
    });

    it('should fall back to spawn when execFile is not available and handle spawn streams', async function() {
        // remove execFile to force spawn path
        child_process.execFile = undefined;

        let used = { spawn: false };
        let captured = null;

        // fake spawn implementation that emits data on stdout and then a close event
        child_process.spawn = function(cmd, argsArray, optsObj) {
            used.spawn = true;
            captured = { cmd: cmd, args: argsArray, opts: optsObj };

            // create a minimal child process with stdout/stderr streams and EventEmitter behavior
            let child = new EventEmitter();
            let stdout = new stream.Readable({
                read() {
                    // no-op; we'll push data asynchronously
                }
            });
            let stderr = new stream.Readable({
                read() {}
            });

            // attach emitters to mimic real child process
            child.stdout = stdout;
            child.stderr = stderr;

            // asynchronously send data and then emit close
            process.nextTick(() => {
                stdout.em})}    })
})