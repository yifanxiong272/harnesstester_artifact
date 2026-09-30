let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports file_0014.resolveMarketplaceInstallShortcut as a function', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0014, 'file_0014 should be present on testpilot_subject');
        assert.strictEqual(
            typeof testpilot_subject.file_0014.resolveMarketplaceInstallShortcut,
            'function',
            'resolveMarketplaceInstallShortcut should be a function'
        );
    });

    })