let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const decorator = testpilot_subject
        && testpilot_subject.file_0002
        && testpilot_subject.file_0002.FsSearchService
        && testpilot_subject.file_0002.FsSearchService.$di$dependencies
        && testpilot_subject.file_0002.FsSearchService.$di$dependencies[1]
        && testpilot_subject.file_0002.FsSearchService.$di$dependencies[1].id;

    it('decorator should exist and be a function', function() {
        assert.strictEqual(typeof decorator, 'function');
    });

    })