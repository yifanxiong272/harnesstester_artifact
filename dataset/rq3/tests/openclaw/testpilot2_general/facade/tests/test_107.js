let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep original function so tests can restore it
    let origParse;

    beforeEach(function() {
        // Save original parseImageSizeError (if any) so we can restore it later
        origParse = testpilot_subject.file_0001.parseImageSizeError;
    });

    afterEach(function() {
        // Restore original to avoid side effects across tests
        testpilot_subject.file_0001.parseImageSizeError = origParse;
    });

    it('returns false for falsy errorMessage values and does not call parseImageSizeError', function() {
        // Replace parseImageSizeError with a function that will fail the test if called
        testpilot_subject.file_0001.parseImageSizeError = function() {
            throw new Error('parseImageSizeError should not be called for falsy input');
        };

        // Call with no argument (undefined)
        assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(), false);

        // Call with null
        assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(null), false);

        // Call with empty string
        assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(''), false);

        // Call with 0 (also falsy)
        assert.strictEqual(testpilot_subject.file_0001.isImageSizeError(0), false);
    });

    })