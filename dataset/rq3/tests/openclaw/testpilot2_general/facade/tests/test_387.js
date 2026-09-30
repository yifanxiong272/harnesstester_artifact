let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0012.sanitizeToolCallId', function() {
    const mod = testpilot_subject.file_0012;
    const sanitize = mod.sanitizeToolCallId;

    it('returns defaulttoolid for non-string / falsy id in default mode', function() {
        assert.strictEqual(sanitize(undefined), 'defaulttoolid');
        assert.strictEqual(sanitize(null), 'defaulttoolid');
        // Note: empty string is falsy and treated like missing id -> defaulttoolid
        assert.strictEqual(sanitize(''), 'defaulttoolid');
    });

    })