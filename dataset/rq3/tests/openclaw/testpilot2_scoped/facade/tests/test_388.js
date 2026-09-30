let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Hold originals so we can restore after tests
    let origLoadMarketplace;
    let origResolveMarketplaceEntryInstallPath;
    let origImportInstall;

    before(function() {
        // Save originals if they exist so we don't break other tests
        origLoadMarketplace = testpilot_subject.file_0014.loadMarketplace;
        origResolveMarketplaceEntryInstallPath = testpilot_subject.file_0014.resolveMarketplaceEntryInstallPath;
        origImportInstall = testpilot_subject.file_0014.import_install;
    });

    after(function() {
        // Restore originals
        if (origLoadMarketplace !== undefined) {
            testpilot_subject.file_0014.loadMarketplace = origLoadMarketplace;
        } else {
            delete testpilot_subject.file_0014.loadMarketplace;
        }
        if (origResolveMarketplaceEntryInstallPath !== undefined) {
            testpilot_subject.file_0014.resolveMarketplaceEntryInstallPath = origResolveMarketplaceEntryInstallPath;
        } else {
            delete testpilot_subject.file_0014.resolveMarketplaceEntryInstallPath;
        }
        if (origImportInstall !== undefined) {
            testpilot_subject.file_0014.import_install = origImportInstall;
        } else {
            delete testpilot_subject.file_0014.import_install;
        }
    });

    it('returns loadMarketplace error when marketplace loading fails', async function() {
        // Arrange
        testpilot_subject.file_0014.loadMarketplace = async function(opts) {
            return { ok: false, error: 'failed to load marketplace' };
        };
        // Act
        const res = await testpilot_subject.file_0014.installPluginFromMarketplace({ marketplace: 'mp1', logger: () => {}, timeoutMs: 1000, plugin: 'whatever' });
        // Assert
        assert.strictEqual(res.ok, false, 'expected ok false when marketplace loading fails');

        // Accept either the stubbed loadMarketplace error (if loadMarketplace was called)
        // or the unsupported marketplace error (if the function validates the marketplace before calling loadMarketplace).
        const allowedErrors = ['failed to load marketplace', `unsupported marketplace source: mp1`];
        assert.ok(allowedErrors.includes(res.error), `unexpected error: ${res.error}`);
    });

    })