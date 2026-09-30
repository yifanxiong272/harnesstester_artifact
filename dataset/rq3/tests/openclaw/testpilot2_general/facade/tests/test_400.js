let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0014.extractToolResultMediaArtifact as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0014, 'module should have file_0014');
        assert.strictEqual(typeof testpilot_subject.file_0014.extractToolResultMediaArtifact, 'function',
            'extractToolResultMediaArtifact should be a function');
    });

    })