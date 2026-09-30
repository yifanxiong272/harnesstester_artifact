let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep references to the original helper functions so we can restore them after tests
    const file = testpilot_subject.file_0017;
    const originals = {
        buildBootstrapTruncationSignature: file.buildBootstrapTruncationSignature,
        normalizeSeenSignatures: file.normalizeSeenSignatures,
        appendSeenSignature: file.appendSeenSignature,
        formatBootstrapTruncationWarningLines: file.formatBootstrapTruncationWarningLines
    };

    // Provide deterministic stub implementations for helper functions used by buildBootstrapPromptWarning.
    before(function() {
        file.buildBootstrapTruncationSignature = function(analysis) {
            // Return null for falsy analysis, otherwise a deterministic signature based on analysis.name or analysis.id
            if (!analysis) return null;
            return 'SIG-' + (analysis.name || analysis.id || 'UNNAMED');
        };

        file.normalizeSeenSignatures = function(input) {
            if (!input) return [];
            if (Array.isArray(input)) return input.slice();
            if (typeof input === 'string') return [input];
            // fallback
            return [];
        };

        file.appendSeenSignature = function(list, sig) {
            const out = (list && Array.isArray(list)) ? list.slice() : [];
            if (!sig) return out;
            // Ensure uniqueness for deterministic tests
            if (!out.includes(sig)) out.push(sig);
            return out;
        };

        file.formatBootstrapTruncationWarningLines = function({analysis, maxFiles}) {
            // Produce a simple, deterministic single-line warning for assertions
            const name = analysis ? (analysis.name || analysis.id || '') : '';
            return [`TRUNCATION:${name}:maxFiles=${maxFiles}`];
        };
    });

    after(function() {
        // Restore original helper functions to avoid side effects
        file.buildBootstrapTruncationSignature = originals.buildBootstrapTruncationSignature;
        file.normalizeSeenSignatures = originals.normalizeSeenSignatures;
        file.appendSeenSignature = originals.appendSeenSignature;
        file.formatBootstrapTruncationWarningLines = originals.formatBootstrapTruncationWarningLines;
    });

    it('does not show warning when mode is "off" and previousSignature is appended to seenSignatures', function() {
        const params = {
            analysis: { name: 'A' },
            seenSignatures: ['prev1'],
            previousSignature: 'prev2',
            mode: 'off',
            maxFiles: 5
        };

        const result = file.buildBootstrapPromptWarning(params);

        // Accept either result.signature or result.truncationSignature to be the derived signature,
        // since implementations may use different property names.
        const expectedSig = file.buildBootstrapTruncationSignature(params.analysis);
        const actualSig = result.signature || result.truncationSignature;
        assert.strictEqual(actualSig, expectedSig, 'expected signature derived from analysis');

        assert.strictEqual(result.warningShown, false, 'warning should not be shown when mode is off');
        assert.deepStrictEqual(result.lines, [], 'lines should be empty when no warning is shown');
        // previousSignature should have been appended before deciding warningSignaturesSeen (mode is off so final list equals seenSignatures after previous append)
        assert.deepStrictEqual(result.warningSignaturesSeen, ['prev1', 'prev2']);
    });

    })