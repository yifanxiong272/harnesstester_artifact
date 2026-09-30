let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Preserve originals so tests do not permanently mutate the module
    let originalRead;
    let originalNormalize;

    beforeEach(function() {
        originalRead = testpilot_subject.readClaudeKnownMarketplaces;
        originalNormalize = testpilot_subject.normalizeEntrySource;
    });

    afterEach(function() {
        // Restore originals (if undefined, delete to return to original state)
        if (typeof originalRead === 'undefined') {
            delete testpilot_subject.readClaudeKnownMarketplaces;
        } else {
            testpilot_subject.readClaudeKnownMarketplaces = originalRead;
        }
        if (typeof originalNormalize === 'undefined') {
            delete testpilot_subject.normalizeEntrySource;
        } else {
            testpilot_subject.normalizeEntrySource = originalNormalize;
        }
    });

    it('should return null for invalid shortcut formats (missing @, leading @, trailing @)', async function() {
        const fn = testpilot_subject.file_0014.resolveMarketplaceInstallShortcut;
        assert.ok(typeof fn === 'function');

        const cases = [
            'plainplugin',
            '@market',
            'plugin@',
            '',           // empty
            '   ',        // whitespace only
            ' /@market',  // plugin slice empty after trim
            'plugin@   '  // marketplaceName empty after trim
        ];

        for (const raw of cases) {
            const res = await fn(raw);
            assert.strictEqual(res, null, `expected null for input "${raw}"`);
        }
    });

    })