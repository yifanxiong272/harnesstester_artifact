let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports testpilot_subject.file_0003.ToolCallComponent as a function', function() {
        assert.ok(testpilot_subject, 'module testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0003, 'module should contain file_0003');
        let ToolCallComponent = testpilot_subject.file_0003.ToolCallComponent;
        assert.strictEqual(typeof ToolCallComponent, 'function', 'ToolCallComponent should be a function or class');
    });

    })