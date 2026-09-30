let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('file_0002.FsSearchService.$di$dependencies[1].id', function() {
        it('should exist and have a toString function', function() {
            // basic existence checks
            assert.ok(testpilot_subject.file_0002, 'file_0002 should exist');
            assert.ok(testpilot_subject.file_0002.FsSearchService, 'FsSearchService should exist');

            const deps = testpilot_subject.file_0002.FsSearchService.$di$dependencies;
            assert.ok(Array.isArray(deps), '$di$dependencies should be an array');
            assert.ok(deps.length > 1, 'should have at least 2 dependencies');

            const dep = deps[1];
            assert.ok(dep && typeof dep === 'object', 'dependency must be an object');
            assert.ok('id' in dep, 'dependency must have id property');
            assert.notStrictEqual(dep.id, undefined, 'id must be defined');
            assert.strictEqual(typeof dep.id.toString, 'function', 'id.toString should be a function');
        });

            })
})