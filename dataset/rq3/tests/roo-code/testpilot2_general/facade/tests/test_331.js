let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject', function() {
    it('exposes file_0007.isValidClineMessage as a function', function() {
        assert.strictEqual(typeof testpilot_subject.file_0007.isValidClineMessage, 'function');
    });

    })