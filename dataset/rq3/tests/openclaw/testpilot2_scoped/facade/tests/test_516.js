let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: try to call a reader function in the common styles: sync return, promise, or callback.
    // cb(err, data)
    function callReader(readerFunc, filePath, cb) {
        let called = false;
        try {
            // Try calling as sync / promise style
            let res = readerFunc(filePath);
            // If returned a thenable (Promise)
            if (res && typeof res.then === 'function') {
                res.then(function(data) {
                    if (called) return;
                    called = true;
                    cb(null, data);
                }).catch(function(err) {
                    if (called) return;
                    called = true;
                    cb(err);
                });
                return;
            }
            // If returned something synchronously (Buffer/string/etc)
            if (typeof res !== 'undefined') {
                cb(null, res);
                return;
            }
        } catch (err) {
            // Synchronous throw
            cb(err);
            return;
        }

        // If we reached here, the reader likely expects a callback style: reader(path, cb)
        // Provide a callback and set a small guard in case the function is actually synchronous and returned undefined.
        let finished = false;
        try {
            readerFunc(filePath, function(err, data) {
                if (finished) return;
                finished = true;
                cb(err, data);
            });
            // give the callback some microtask time if it might be async. If the function neither returned nor invoked the callback,
            // we'll wait a short while then call cb with an error.
            setTimeout(function() {
                if (!finished) {
                    finished = true;
                    cb(new Error('Reader did not return a value, a promise, throw, or call a callback within timeout'));
                }
            }, 200);
        } catch (err) {
            cb(err);
        }
    }

    it('createRootScopedReadFile should exist and be a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject module is present');
        assert.strictEqual(typeof testpilot_subject.file_0018.createRootScopedReadFile, 'function',
            'createRootScopedReadFile should be a function');
    });

    })