let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.FsService.resolveDownload - unit tests (self-contained)', function() {
    let FsService;

    before(function() {
        // Locate the FsService constructor in the imported module.
        // The path hinted in the prompt is testpilot_subject.file_0004.FsService
        // but be defensive in case of minor differences.
        if (testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.FsService) {
            FsService = testpilot_subject.file_0004.FsService;
        } else {
            // Expose helpful failure if structure is unexpected.
            FsService = undefined;
        }
    });

    it('exports FsService constructor at testpilot_subject.file_0004.FsService', function() {
        assert.ok(FsService, 'FsService should be exported at testpilot_subject.file_0004.FsService');
        assert.strictEqual(typeof FsService, 'function', 'FsService should be a constructor function');
    });

    })