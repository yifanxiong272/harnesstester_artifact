let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0007.buildIrcNickServCommands', function() {
    const build = testpilot_subject.file_0007.buildIrcNickServCommands;

    it('returns [] when options is missing', function() {
        assert.deepStrictEqual(build(), []);
    });

    })