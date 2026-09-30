let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const createProcessTool = testpilot_subject &&
                              testpilot_subject.file_0005 &&
                              testpilot_subject.file_0005.createProcessTool;

    it('createProcessTool should exist and be a function', function() {
        assert.strictEqual(typeof createProcessTool, 'function', 'createProcessTool must be a function');
    });

    })