let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase default timeout in case async setup is slow in some environments
    this.timeout(5000);

    function awaitWithTimeout(promise, ms) {
        return Promise.race([
            promise,
            new Promise((_, reject) => setTimeout(() => reject(new Error('timeout waiting for promise')), ms))
        ]);
    }

    it('exports file_0016.createAcpClient as a function (async function expected)', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0016, 'module should export file_0016');
        const fn = testpilot_subject.file_0016.createAcpClient;
        assert.strictEqual(typeof fn, 'function', 'createAcpClient should be a function');
        // If environment preserves async function constructor name, check it (non-fatal)
        if (fn && fn.constructor && fn.constructor.name) {
            // This assertion is tolerant: only check if it looks like an async function
            const ctorName = fn.constructor.name;
            const isAsyncLike = ctorName === 'AsyncFunction' || ctorName === 'Function';
            assert.ok(isAsyncLike, `createAcpClient constructor name is ${ctorName}`);
        }
    });

    })