let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const idfn = (() => {
        // Guard to produce a helpful error if the path is wrong
        if (!testpilot_subject ||
            !testpilot_subject.file_0001 ||
            !testpilot_subject.file_0001.FsWatcherService ||
            !testpilot_subject.file_0001.FsWatcherService.$di$dependencies ||
            !Array.isArray(testpilot_subject.file_0001.FsWatcherService.$di$dependencies) ||
            testpilot_subject.file_0001.FsWatcherService.$di$dependencies.length === 0 ||
            typeof testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0].id !== 'function') {
            throw new Error('Could not locate testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0].id');
        }
        return testpilot_subject.file_0001.FsWatcherService.$di$dependencies[0].id;
    })();

    it('should exist and be a function', function() {
        assert.strictEqual(typeof idfn, 'function', 'id should be a function');
    });

    })