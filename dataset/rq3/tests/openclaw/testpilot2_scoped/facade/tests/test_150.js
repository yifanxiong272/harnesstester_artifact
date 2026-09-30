let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0001.parseImageSizeError as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0001, 'file_0001 should exist');
        assert.equal(typeof testpilot_subject.file_0001.parseImageSizeError, 'function',
            'parseImageSizeError should be a function');
    });

    })