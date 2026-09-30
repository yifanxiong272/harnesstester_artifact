let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.isImageSizeError - unit tests', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0001 &&
               testpilot_subject.file_0001.isImageSizeError;

    it('should export a function', function() {
        assert.strictEqual(typeof fn, 'function', 'isImageSizeError should be a function');
    });

    })