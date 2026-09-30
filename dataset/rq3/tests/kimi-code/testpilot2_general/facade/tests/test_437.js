let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('test testpilot_subject.file_0008.createInitialState - returns an object (not null)', function() {
        let s = testpilot_subject.file_0008.createInitialState();
        assert.notStrictEqual(s, null, 'createInitialState should not return null');
        assert.strictEqual(typeof s, 'object', 'createInitialState should return an object or array');
    });

    })