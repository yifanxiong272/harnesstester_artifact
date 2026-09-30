let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('structure: should have file_0002.FsSearchService.$di$dependencies[1].id with a toString function', function() {
        // navigate to the target
        assert.ok(testpilot_subject, 'testpilot_subject must be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 must be present');
        assert.ok(testpilot_subject.file_0002.FsSearchService, 'FsSearchService must be present');
        assert.ok(Array.isArray(testpilot_subject.file_0002.FsSearchService.$di$dependencies),
                  '$di$dependencies must be an array');
        assert.ok(testpilot_subject.file_0002.FsSearchService.$di$dependencies.length > 1,
                  '$di$dependencies must have at least 2 entries');
        let dep = testpilot_subject.file_0002.FsSearchService.$di$dependencies[1];
        assert.ok(dep && dep.id, 'second dependency must have an id');
        assert.strictEqual(typeof dep.id.toString, 'function', 'id.toString should be a function');
    });

    })