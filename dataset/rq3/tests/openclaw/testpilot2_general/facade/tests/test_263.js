let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.renderExecHostLabel', function() {
    const render = testpilot_subject.file_0009.renderExecHostLabel;

    it('should be a function', function() {
        assert.strictEqual(typeof render, 'function', 'renderExecHostLabel must be a function');
    });

    })