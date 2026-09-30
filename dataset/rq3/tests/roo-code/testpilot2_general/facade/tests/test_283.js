let mocha = require('mocha');
let assert = require('assert');
let os = require('os');
let path = require('path');
let fs = require('fs');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic sanity: the method exists and is declared as an async function
    it('test testpilot_subject.file_0006.WorktreeService.prototype.checkoutBranch - is async function', function() {
        const fn = testpilot_subject.file_0006.WorktreeService.prototype.checkoutBranch;
        assert.strictEqual(typeof fn, 'function', 'checkoutBranch should be a function on the prototype');
        // Async functions have constructor name "AsyncFunction"
        assert.strictEqual(fn.constructor.name, 'AsyncFunction', 'checkoutBranch should be an async function');
    });

    // Calling with a non-existing working directory should reject (we don't rely on external resources;
    // the method is expected to fail quickly when cwd is invalid)
    })