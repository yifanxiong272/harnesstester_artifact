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

    it('should call execFile and resolve when execFile returns success', async function() {
        let used = { execFile: false, spawn: false };
        let captured = null;

        // fake execFile implementation that normalizes arguments and invokes callback with stdout
        child_process.execFile = function(cmd, a, o, cb) {
            used.execFile = true;
            let argsArray, optsObj, callback;
            if (typeof a === 'function') {
                argsArray = [];
                optsObj = {};
                callback = a;
            } else if (typeof o === 'function') {
                argsArray = a;
                optsObj = {};
                callback = o;
            } else {
                argsArray = a;
                optsObj = o;
                callback = cb;
            }
            captured = { cmd: cmd, args: argsArray, opts: optsObj };
            // simulate async successful execution
            process.nextTick(() => callback(null, 'fake-stdout-data', ''));
            // execFile normally returns a ChildProcess; a minimal object is fine
            return { pid: 12345 };
        };

        // allow spawn path as well (some implementations use spawn instead of execFile)
        child_process.spawn = function(cmd, a, o) {
            used.spawn = true;
            let argsArray = [];
            let optsObj = {};
            if (Array.isArray(a)) {
                argsArray = a;
                optsObj = o || {};
            } else if (Array.isArray(o)) {
                // unlikely, but normalize
                argsArray = o;
                optsObj = {};
            } else if (a && typeof a === 'object' && !Array.isArray(a)) {
                // spawn(command, options) (no args)
                argsArray = [];
                optsObj = a;
            }
            captured = { cmd: cmd, args: argsArray, opts: optsObj };

            // create a minimal ChildProcess-like object with stdout/stderr streams and EventEmitter
            let child = new EventEmitter();
            child.stdout = new stream.PassThrough();
            child.stderr = new stream.PassThrough();

            // simulate async data and normal exit
            process.nextTick(() => {
                child.stdout.write('fake-stdout-data');
                child.stdout.end();
                child.em})}    })
})