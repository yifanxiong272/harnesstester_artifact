let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0008;

    it('does nothing when prepend is not an array', function() {
        const env = { SOME_KEY: 'value' };
        // Should return early and not modify env
        subject.applyPathPrepend(env, null, {});
        assert.deepStrictEqual(env, { SOME_KEY: 'value' });
    });

    })