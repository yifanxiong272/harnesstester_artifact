let mocha = require('mocha');
let assert = require('assert');
let child_process = require('child_process');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const WorktreeService = testpilot_subject.file_0006.WorktreeService;
    let originalExec;
    let stubBehavior;

    // simple stub wrapper that captures args and delegates to stubBehavior
    beforeEach(function() {
        originalExec = child_process.exec;
        stubBehavior = null;
        child_process.exec = function(cmd, options, cb) {
            if (typeof options === 'function') { cb = options; options = undefined; }
            // ensure async behavior similar to real exec
            if (!stubBehavior) {
                // default: simulate failure
                setImmediate(() => cb(new Error('no stubBehavior set'), '', ''));
            } else {
                return stubBehavior(cmd, options, cb);
            }
            // return a minimal stub ChildProcess-like object
            return { pid: 0, kill: () => {} };
        };
    });

    afterEach(function() {
        // restore the original exec so other tests / code are not affected
        child_process.exec = originalExec;
    });

    it('returns trimmed stdout when git rev-parse succeeds', async function() {
        const cwdArg = '/some/repo';
        let observed = null;
        stubBehavior = function(cmd, options, cb) {
            // verify the command and options that the function uses
            observed = { cmd, options };

            // Provide both callback-based and stream-based (stdout) behavior,
            // since implementations may use either the exec callback or the
            // child process stdout/close events.
            const EventEmitter = require('events');
            const stdout = new EventEmitter();
            const cp = new EventEmitter();
            cp.stdout = stdout;
            cp.pid = 1234;
            cp.kill = () => {};

            // Emit data and close events asynchronously, and also call the callback.
            setImmediate(() => {
                if (typeof cb === 'function') {
                    cb(null, '   /some/repo/path/ \n', '');
                }
                stdout.em})}    })
})