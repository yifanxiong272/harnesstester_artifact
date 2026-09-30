let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Locate the target object/function under test
    let dep;
    try {
        dep = testpilot_subject.file_0002.FsSearchService.$di$dependencies[0].id;
    } catch (e) {
        // If structure is not present the tests should fail with a clear message
        dep = undefined;
    }

    it('should have the id object present', function() {
        assert.ok(dep, 'Expected testpilot_subject.file_0002.FsSearchService.$di$dependencies[0].id to exist');
    });

    })