let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const spa = testpilot_subject.file_0026 && testpilot_subject.file_0026.ToolInputSchema && testpilot_subject.file_0026.ToolInputSchema.spa;

    it('spa should exist and be a function', function() {
        assert.ok(spa, 'spa is not exported');
        assert.strictEqual(typeof spa, 'function');
    });

    })