let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call the prototype method with a fake "this" object
    function callBuildHeader(toolCall, result, overrides = {}) {
        const fakeThis = {
            toolCall,
            result,
            workspaceDir: overrides.workspaceDir || "",
            // Provide simple stubs for methods the buildHeader may call on `this`.
            buildHeaderChip: overrides.buildHeaderChip || function(r) { return ""; },
            isSingleSubagentView: overrides.isSingleSubagentView || function() { return false; },
            buildSingleSubagentHeader: overrides.buildSingleSubagentHeader || function() { return ""; }
        };
        return testpilot_subject.file_0003.ToolCallComponent.prototype.buildHeader.call(fakeThis);
    }

    it('generic tool (not finished) should indicate Using and include tool name', function(done) {
        const toolCall = { name: "MyTool", args: {}, truncated: false };
        const result = undefined; // not finished
        const header = callBuildHeader(toolCall, result);
        assert.ok(typeof header === "string", "header should be a string");
        assert.ok(header.indexOf("Using") !== -1, "expected header to include 'Using'");
        assert.ok(header.indexOf("MyTool") !== -1, "expected header to include tool name");
        done();
    });

    })