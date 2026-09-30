let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const parse = testpilot_subject.file_0016.default.configSchema.parse;

    it('exported parse should be a function', function() {
        assert.strictEqual(typeof parse, 'function');
    });

    })