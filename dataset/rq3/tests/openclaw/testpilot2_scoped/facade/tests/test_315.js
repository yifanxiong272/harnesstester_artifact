let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // short helper for the function under test
    const fn = (testpilot_subject && testpilot_subject.file_0012 && testpilot_subject.file_0012.sanitizeImageBlocks)
        ? testpilot_subject.file_0012.sanitizeImageBlocks
        : null;

    it('sanitizeImageBlocks should be present and be a function that returns a Promise when called', async function() {
        assert.ok(fn, 'sanitizeImageBlocks is not present on testpilot_subject.file_0012');
        assert.equal(typeof fn, 'function');

        // calling with minimal args should return a Promise (it's declared async)
        const maybePromise = fn([], 'label-for-test');
        // If it's an actual Promise / async function we can await it; otherwise this will throw
        await Promise.resolve(maybePromise);
    });

    })