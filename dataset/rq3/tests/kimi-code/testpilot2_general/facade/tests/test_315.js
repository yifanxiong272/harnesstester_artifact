let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic sanity checks that do not touch the file system or external resources.
    it('exports file_0004 and FsService', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0004, 'file_0004 namespace should be present');
        assert.ok(testpilot_subject.file_0004.FsService, 'FsService should be exported');
    });

    })