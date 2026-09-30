let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // get a reference to the id function under test in a safe way
    let deps = testpilot_subject
        && testpilot_subject.file_0002
        && testpilot_subject.file_0002.FsSearchService
        && testpilot_subject.file_0002.FsSearchService['$di$dependencies'];
    let idFn = Array.isArray(deps) && deps.length > 1 && deps[1].id;

    it('should have an id function at the expected location', function() {
        assert.ok(deps, 'expected $di$dependencies to exist and be an array-like value');
        assert.ok(idFn, 'expected deps[1].id to exist');
        assert.strictEqual(typeof idFn, 'function', 'id should be a function');
    });

    })