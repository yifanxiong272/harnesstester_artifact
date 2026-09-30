let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const gen = testpilot_subject.file_0001.generateCodeVerifier;

    it('returns a string', function() {
        const v = gen();
        assert.strictEqual(typeof v, 'string');
    });

    })