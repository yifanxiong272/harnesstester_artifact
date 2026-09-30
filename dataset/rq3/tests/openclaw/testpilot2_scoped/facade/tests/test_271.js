let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

const child_process = require('child_process');
const stream = require('stream');
const EventEmitter = require('events').EventEmitter;

describe('test testpilot_subject', function() {
    // Keep original spawn so we can restore it after tests
    let originalSpawn;

    beforeEach(function() {
        originalSpawn = child_process.spawn;
    });

    afterEach(function() {
        // Restore original spawn after each test to avoid side effects
        child_process.spawn = originalSpawn;
    });

    it('test testpilot_subject.file_0008.runExecProcess - spawns with provided command/args and resolves (captures stdout)', async function() {
        let spawnCalled = false;
        let captured = null;

        // Fake spawn: returns an object that behaves like a ChildProcess,
        // with stdout/stderr streams and emits a 'close' (or 'exit') event.
        child_process.spawn = function(cmd, args, options) {
            spawnCalled = true;
            captured = { cmd: cmd, args: args, options: options };

            // Mock child process
            const mockProc = new EventEmitter();
            mockProc.pid = 12345;
            mockProc.kill = function() { /* noop */ };

            // stdout/stderr as streams
            mockProc.stdout = new stream.PassThrough();
            mockProc.stderr = new stream.PassThrough();

            // Simulate the child writing to stdout, then exiting successfully
            process.nextTick(() => {
                mockProc.stdout.write('hello-from-child\n');
                mockProc.stdout.end();
                mockProc.stderr.write(''); // nothing on stderr
                mockProc.stderr.end();
                // Many Node APIs emit 'close' with the exit code; some emit 'exit'.
                mockProc.em})}    })
})