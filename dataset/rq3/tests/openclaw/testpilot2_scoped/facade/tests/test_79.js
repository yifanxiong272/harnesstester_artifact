let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const sut = testpilot_subject && testpilot_subject.file_0001;
    it('exports file_0001 and isFailoverErrorMessage is a function', function() {
        assert.ok(sut, 'expected testpilot_subject.file_0001 to be present');
        assert.strictEqual(typeof sut.isFailoverErrorMessage, 'function', 'isFailoverErrorMessage should be a function');
    });

    })