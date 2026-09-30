let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0001.isImageSizeError - falsy errorMessage returns false', function() {
        // Grab the original function source so we can re-bind parseImageSizeError in a controlled way.
        const src = testpilot_subject.file_0001.isImageSizeError.toString();

        // Create a version of the function that uses our stubbed parseImageSizeError.
        // The IIFE creates a closure so that the inner function's reference to
        // parseImageSizeError is resolved to our stub.
        const stubParse = function() { throw new Error('parseImageSizeError should not be called for falsy messages'); };
        const isImageSizeError = eval('(function(parseImageSizeError){ return ' + src + '})')(stubParse);

        // falsy inputs should short-circuit and return false without calling parseImageSizeError
        assert.strictEqual(isImageSizeError(null), false);
        assert.strictEqual(isImageSizeError(undefined), false);
        assert.strictEqual(isImageSizeError(''), false);
    });

    })