let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const fn = testpilot_subject.file_0009.findPathKey;

    it('returns "PATH" when PATH exists as own property', function() {
        const env = { PATH: '/usr/bin' };
        assert.strictEqual(fn(env), 'PATH');
    });

    })