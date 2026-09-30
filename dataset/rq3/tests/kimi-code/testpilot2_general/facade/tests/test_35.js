let mocha = require('mocha');
let assert = require('assert');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // A small timeout so tests that hang will fail quickly
    this.timeout(2000);

    function tryCallGrep(fn, cwd, req, signal, startedAt) {
        // Try to call the async function and normalize outcomes:
        // - If it throws synchronously, return a rejected Promise with that error.
        // - If it returns a thenable, return that thenable.
        // - Otherwise, return a resolved Promise with the result (so tests can detect unexpected sync return).
        try {
            let res = fn.call({}, cwd, req, signal, startedAt);
            if (res && typeof res.then === 'function') {
                return res;
            }
            // non-thenable returned synchronously
            return Promise.resolve(res);
        } catch (err) {
            return Promise.reject(err);
        }
    }

    it('should export grepWithNode as an async function on the prototype', function() {
        // Check existence
        assert.ok(testpilot_subject, 'module testpilot_subject must be present');
        assert.ok(testpilot_subject.file_0002, 'module file_0002 must be present');
        const protoFn = testpilot_subject.file_0002.FsSearchService && testpilot_subject.file_0002.FsSearchService.prototype && testpilot_subject.file_0002.FsSearchService.prototype.grepWithNode;
        assert.ok(protoFn, 'grepWithNode must exist on prototype');

        // Async functions have constructor name 'AsyncFunction' in Node
        assert.strictEqual(protoFn.constructor && protoFn.constructor.name, 'AsyncFunction', 'grepWithNode should be declared async');
    });

    })