let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0004.FsService.prototype.dispose - API surface', function() {
        // Ensure the constructor and prototype method exist
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0004, 'file_0004 namespace should be present');
        const FsService = testpilot_subject.file_0004.FsService;
        assert.ok(FsService, 'FsService should be present');
        assert.strictEqual(typeof FsService.prototype.dispose, 'function', 'dispose should be a function on the prototype');
    });

    })