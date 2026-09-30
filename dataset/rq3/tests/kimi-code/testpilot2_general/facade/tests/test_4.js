let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const diDeps = testpilot_subject &&
                   testpilot_subject.file_0002 &&
                   testpilot_subject.file_0002.FsSearchService &&
                   testpilot_subject.file_0002.FsSearchService.$di$dependencies;

    it('has an id function at file_0002.FsSearchService.$di$dependencies[0].id', function() {
        assert.ok(Array.isArray(diDeps), '$di$dependencies should be an array');
        assert.ok(diDeps.length > 0, '$di$dependencies should contain at least one entry');
        const first = diDeps[0];
        assert.ok(first, 'first dependency entry should exist');
        assert.strictEqual(typeof first.id, 'function', 'id should be a function');
    });

    })