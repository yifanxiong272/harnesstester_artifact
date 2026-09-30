let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0012.sanitizeToolResultImages', function() {

        it('should exist and return a Promise when invoked', function() {
            const fn = testpilot_subject.file_0012.sanitizeToolResultImages;
            assert.strictEqual(typeof fn, 'function', 'sanitizeToolResultImages should be a function');
            // Calling with a minimal input should return a Promise (it's declared async)
            const ret = fn({}, 'label');
            assert(ret && typeof ret.then === 'function', 'should return a Promise');
            // Return the promise so Mocha waits for resolution/rejection
            return ret;
        });

            })
})