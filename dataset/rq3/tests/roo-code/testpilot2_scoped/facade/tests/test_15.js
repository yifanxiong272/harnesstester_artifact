let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0004.extractCommandBlocks', function() {
    let fn = testpilot_subject &&
             testpilot_subject.file_0004 &&
             testpilot_subject.file_0004.extractCommandBlocks;

    it('should be a function', function() {
        assert.strictEqual(typeof fn, 'function', 'extractCommandBlocks should be a function');
    });

    })