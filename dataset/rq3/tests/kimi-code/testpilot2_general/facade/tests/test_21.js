let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0002.FsSearchService.prototype.dispose - existence', function() {
        // Ensure the module and the constructor/prototype exist
        assert.ok(testpilot_subject, 'testpilot_subject module must be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 namespace must be present');
        let FsSearchService = testpilot_subject.file_0002.FsSearchService;
        assert.ok(FsSearchService, 'FsSearchService must be present');
        assert.strictEqual(typeof FsSearchService.prototype.dispose, 'function',
            'FsSearchService.prototype.dispose must be a function');
    });

    })