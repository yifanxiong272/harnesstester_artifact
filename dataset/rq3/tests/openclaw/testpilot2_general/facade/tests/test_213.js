let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let {promises: fsp} = fs;
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case applyPatch does something that takes a bit longer
    this.timeout(5000);

    it('test testpilot_subject.file_0008.createApplyPatchTool - returns tool metadata', function() {
        const tool = testpilot_subject.file_0008.createApplyPatchTool();
        assert.ok(tool);
        assert.strictEqual(tool.name, 'apply_patch');
        assert.strictEqual(tool.label, 'apply_patch');
        assert.ok(typeof tool.execute === 'function');
        assert.ok(tool.parameters, 'tool.parameters should exist');
    });

    })