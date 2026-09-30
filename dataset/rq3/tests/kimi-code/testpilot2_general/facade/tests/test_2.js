let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0002.FsSearchService as a function/class', function() {
        assert.ok(testpilot_subject, 'module should be require-able');
        assert.ok(testpilot_subject.file_0002, 'module should have file_0002 property');
        let FsSearchService = testpilot_subject.file_0002 && testpilot_subject.file_0002.FsSearchService;
        assert.ok(FsSearchService, 'FsSearchService should be exported');
        assert.strictEqual(typeof FsSearchService, 'function', 'FsSearchService should be a function or class');
    });

    })