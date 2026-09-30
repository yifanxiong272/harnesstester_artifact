let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('should return the exact key name when env has an uppercase PATH key', function() {
        let env = { PATH: '/usr/bin' };
        let key = testpilot_subject.file_0008.findPathKey(env);
        assert.strictEqual(key, 'PATH');
        // ensure value remains unchanged
        assert.strictEqual(env.PATH, '/usr/bin');
    });

    })