let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0013.resolveDockerSpawnInvocation - is exported and is a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0013, 'module should export file_0013');
        assert.strictEqual(typeof testpilot_subject.file_0013.resolveDockerSpawnInvocation, 'function',
            'resolveDockerSpawnInvocation should be a function');
    });

    })