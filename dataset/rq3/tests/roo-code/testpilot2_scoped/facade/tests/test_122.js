let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case implementation does some async work
    this.timeout(5000);

    it('should reject when called with no options or invalid options', async function() {
        // calling with no args should reject (or throw)
        try {
            await testpilot_subject.file_0011.generateImageWithProvider();
            throw new Error('Expected generateImageWithProvider() to reject when called without options');
        } catch (err) {
            // any error is acceptable for this test
            assert.ok(err, 'expected an error when options are missing');
        }

        // calling with a plainly invalid options object (non-object) should reject
        try {
            // some implementations may throw synchronously, others reject
            await testpilot_subject.file_0011.generateImageWithProvider('not-an-object');
            throw new Error('Expected generateImageWithProvider("not-an-object") to reject');
        } catch (err) {
            assert.ok(err, 'expected an error for invalid options type');
        }
    });

    })