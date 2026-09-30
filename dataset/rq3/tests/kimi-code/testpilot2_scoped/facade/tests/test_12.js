let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const decorator = testpilot_subject.file_0001.FsWatcherService.$di$dependencies[1].id;

    it('should be a function', function() {
        assert.strictEqual(typeof decorator, 'function');
    });

    })