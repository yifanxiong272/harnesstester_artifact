let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0007.buildIrcNickServCommands', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0007 &&
               testpilot_subject.file_0007.buildIrcNickServCommands;

    it('exists and is a function', function() {
        assert.ok(fn, 'function buildIrcNickServCommands should exist');
        assert.strictEqual(typeof fn, 'function');
    });

    })