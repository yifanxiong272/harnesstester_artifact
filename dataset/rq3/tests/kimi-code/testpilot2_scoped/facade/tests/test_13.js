let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to get the targeted path; using a helper lets tests fail with clearer messages
    function getDependencies() {
        assert.ok(testpilot_subject, 'testpilot_subject module must be present');
        assert.ok(testpilot_subject.file_0001, 'testpilot_subject.file_0001 must be present');
        assert.ok(testpilot_subject.file_0001.FsWatcherService, 'FsWatcherService must be present');
        const deps = testpilot_subject.file_0001.FsWatcherService.$di$dependencies;
        return deps;
    }

    it('should expose $di$dependencies as an array with at least two entries', function() {
        const deps = getDependencies();
        assert.ok(Array.isArray(deps), '$di$dependencies should be an array');
        assert.ok(deps.length > 1, 'expected at least 2 dependencies');
    });

    })