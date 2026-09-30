let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exposes file_0003.setMinComponentLines as a function', function() {
        assert.strictEqual(
            typeof testpilot_subject.file_0003.setMinComponentLines,
            'function',
            'setMinComponentLines should be a function'
        );
    });

    })