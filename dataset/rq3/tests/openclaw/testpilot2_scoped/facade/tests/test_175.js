let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let fn = testpilot_subject && testpilot_subject.file_0004 && testpilot_subject.file_0004.cleanSchemaForGemini;

    it('cleanSchemaForGemini should exist', function() {
        assert.ok(typeof fn === 'function', 'cleanSchemaForGemini is not a function');
    });

    })