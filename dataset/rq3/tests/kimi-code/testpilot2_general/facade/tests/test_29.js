let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0002.FsSearchService.prototype.probeRg', function() {
        it('should exist on the prototype and be a function', function() {
            assert.ok(testpilot_subject, 'testpilot_subject module should be present');
            assert.ok(testpilot_subject.file_0002, 'file_0002 should be present on module');
            assert.ok(testpilot_subject.file_0002.FsSearchService, 'FsSearchService should be present');
            const proto = testpilot_subject.file_0002.FsSearchService.prototype;
            assert.ok(proto, 'FsSearchService.prototype should exist');
            assert.strictEqual(typeof proto.probeRg, 'function', 'probeRg should be a function on the prototype');
        });

            })
})