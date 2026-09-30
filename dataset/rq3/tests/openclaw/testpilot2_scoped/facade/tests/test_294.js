let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0010.resolveExecDetail', function() {
    const file = testpilot_subject.file_0010 || {};
    const originals = {
        asRecord: file.asRecord,
        import_tool_display_exec_shell: file.import_tool_display_exec_shell && file.import_tool_display_exec_shell.unwrapShellWrapper,
        summarizeExecCommand: file.summarizeExecCommand,
        compactRawCommand: file.compactRawCommand,
        isGenericSummary: file.isGenericSummary
    };

    // Helper to safely set a nested importer object
    function ensureImporter() {
        if (!file.import_tool_display_exec_shell) {
            file.import_tool_display_exec_shell = {};
        }
    }

    beforeEach(function() {
        // Provide deterministic, test-controlled helpers for each test.
        // asRecord: accept plain objects only
        file.asRecord = function (args) {
            return args && typeof args === 'object' ? args : undefined;
        };

        ensureImporter();
        // unwrapShellWrapper: identity by default
        file.import_tool_display_exec_shell.unwrapShellWrapper = function (raw) {
            return raw;
        };

        // default: no summary found (generic fallback)
        file.summarizeExecCommand = function () {
            return undefined;
        };

        // compact: just return the unwrapped command trimmed
        file.compactRawCommand = function (unwrapped) {
            return typeof unwrapped === 'string' ? unwrapped.trim() : undefined;
        };

        // generic summary detector: treat "run command" as generic by default
        file.isGenericSummary = function (summary) {
            return summary === 'run command';
        };
    });

    after(function() {
        // Restore originals
        if (originals.asRecord === undefined) {
            delete file.asRecord;
        } else {
            file.asRecord = originals.asRecord;
        }

        if (originals.import_tool_display_exec_shell === undefined) {
            if (file.import_tool_display_exec_shell) {
                delete file.import_tool_display_exec_shell.unwrapShellWrapper;
            }
        } else {
            file.import_tool_display_exec_shell.unwrapShellWrapper = originals.import_tool_display_exec_shell;
        }

        if (originals.summarizeExecCommand === undefined) {
            delete file.summarizeExecCommand;
        } else {
            file.summarizeExecCommand = originals.summarizeExecCommand;
        }

        if (originals.compactRawCommand === undefined) {
            delete file.compactRawCommand;
        } else {
            file.compactRawCommand = originals.compactRawCommand;
        }

        if (originals.isGenericSummary === undefined) {
            delete file.isGenericSummary;
        } else {
            file.isGenericSummary = originals.isGenericSummary;
        }
    });

    it('returns undefined for null/invalid args', function() {
        assert.strictEqual(file.resolveExecDetail(null), undefined);
        assert.strictEqual(file.resolveExecDetail("not an object"), undefined);
    });

    })