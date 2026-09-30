let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic availability check
    it('CacheStrategy should be available', function() {
        assert.ok(testpilot_subject.file_0010, 'file_0010 namespace missing');
        assert.ok(testpilot_subject.file_0010.CacheStrategy, 'CacheStrategy missing');
    });

    })