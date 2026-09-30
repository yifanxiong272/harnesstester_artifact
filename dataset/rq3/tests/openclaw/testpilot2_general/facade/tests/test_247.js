let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Get reference to the function under test
    const findPathKey = testpilot_subject &&
                        testpilot_subject.file_0009 &&
                        testpilot_subject.file_0009.findPathKey;

    it('findPathKey should be a function', function() {
        assert.strictEqual(typeof findPathKey, 'function');
    });

    })