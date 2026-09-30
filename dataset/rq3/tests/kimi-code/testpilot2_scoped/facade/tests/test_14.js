let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let id;

    before(function() {
        // Basic existence checks so tests fail with clear messages if the structure isn't present
        assert.ok(testpilot_subject, 'module "testpilot_subject" is not available');
        assert.ok(testpilot_subject.file_0001, 'testpilot_subject.file_0001 is not present');
        assert.ok(testpilot_subject.file_0001.FsWatcherService, 'FsWatcherService is not present');
        assert.ok(testpilot_subject.file_0001.FsWatcherService.$di$dependencies, '$di$dependencies is not present');
        assert.ok(testpilot_subject.file_0001.FsWatcherService.$di$dependencies.length > 1,
            '$di$dependencies does not contain an element at index 1');
        id = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[1].id;
        assert.ok(id, 'id at index 1 is not present');
    });

    it('has a toString function', function() {
        assert.strictEqual(typeof id.toString, 'function', 'id.toString should be a function');
    });

    })