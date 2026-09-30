let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports reduceAppEvent as a function', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.strictEqual(typeof testpilot_subject.file_0008.reduceAppEvent, 'function',
            'reduceAppEvent should be a function');
    });

    })