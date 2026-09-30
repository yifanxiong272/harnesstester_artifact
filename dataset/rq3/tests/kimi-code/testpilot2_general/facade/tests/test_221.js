let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Short alias to the module piece that contains the ToolCallComponent
    const mod = testpilot_subject.file_0003;

    // Provide safe mocks for theme and formatting helper functions that the method uses.
    // We attach them to the module namespace so the method (which references these names)
    // will pick up our test-friendly implementations.
    beforeEach(function() {
        // Simple theme mock: fg marks the content with [role:content], dim wraps with <dim>...</dim>
        mod.import_theme = {
            currentTheme: {
                fg: (role, content) => `[${role}:${content}]`,
                dim: (s) => `<dim>${s}</dim>`
            }
        };

        // Default token formatters; individual tests can override these if needed.
        mod.formatSubagentContextTokens = function() { return undefined; };
        mod.formatSubagentTokens = function() { return undefined; };
    });

    it('returns empty string when subagentPhase is undefined', function() {
        const obj = Object.create(mod.ToolCallComponent.prototype);
        // no subagentPhase set
        const out = obj.formatPhaseChip();
        assert.strictEqual(out, "");
    });

    })