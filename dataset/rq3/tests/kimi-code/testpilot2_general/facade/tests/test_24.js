let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Basic smoke tests for FsSearchService.prototype.dispose
    it('dispose should exist and be a function', function() {
        const serviceModule = testpilot_subject && testpilot_subject.file_0002;
        assert.ok(serviceModule, 'module file_0002 should exist on testpilot_subject');
        const FsSearchService = serviceModule.FsSearchService;
        assert.ok(FsSearchService, 'FsSearchService should be exported');
        assert.strictEqual(typeof FsSearchService.prototype.dispose, 'function', 'dispose should be a function on the prototype');
    });

    })