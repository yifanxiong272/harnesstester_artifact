let mocha = require('mocha');
let assert = require('assert');
let child_process = require('child_process');
let EventEmitter = require('events');

describe('test testpilot_subject', function() {
    // require the module under test lazily inside tests so we can stub child_process.exec first
    let originalExec;

    beforeEach(function() {
        // save original exec and replace with a stub we control in each test
        originalExec = child_process.exec;
    });

    afterEach(function() {
        // restore original exec after each test to avoid side effects
        child_process.exec = originalExec;
        originalExec = null;
        // clear require cache for module under test so it will pick up the restored exec if it required child_process earlier
        try {
            delete require.cache[require.resolve('testpilot_subject')];
        } catch (e) {
            // ignore if module not present
        }
    });

    it('propagates errors from child_process.exec as a rejected promise', async function() {
        // Arrange: stub exec to simulate an error (e.g., docker not available)
        // Return a fake ChildProcess (EventEmitter) and also call the callback with an error.
        child_process.exec = function(cmd, callback) {
            const child = new EventEmitter();
            setImmediate(() => {
                const err = new Error('simulated exec failure');
                // emit error event for implementations that listen on the child process
                child.em})}    })
})