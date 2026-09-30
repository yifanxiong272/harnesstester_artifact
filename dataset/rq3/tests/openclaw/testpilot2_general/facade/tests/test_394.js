let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fnPath = ['file_0013', 'resolveExecDetail'];
    it('should expose testpilot_subject.file_0013.resolveExecDetail as a function', function() {
        // Basic existence test
        assert.ok(testpilot_subject, 'testpilot_subject module must be present');
        assert.ok(testpilot_subject.file_0013, 'testpilot_subject.file_0013 must be present');
        assert.strictEqual(typeof testpilot_subject.file_0013.resolveExecDetail, 'function',
            'resolveExecDetail should be a function');
    });

    // helper to call the function and normalize sync/async returns into a Promise
    function callResolveExecDetail(args) {
        try {
            const result = testpilot_subject.file_0013.resolveExecDetail(args);
            // If it returns a promise-like, wrap with Promise.resolve
            return Promise.resolve(result);
        } catch (err) {
            // preserve thrown synchronous errors as a rejected promise
            return Promise.reject(err);
        }
    }

    })