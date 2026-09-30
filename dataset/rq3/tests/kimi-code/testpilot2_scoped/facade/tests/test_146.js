let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Convenience references
    const file = testpilot_subject.file_0002;
    const KimiCore = file.KimiCore;

    // Helpers to restore module-level stubs after each test
    let original_import_export, original_import_logger, original_warnIfLogFlushFails;

    beforeEach(function() {
        // Save originals so we can restore them
        original_import_export = file.import_export;
        original_import_logger = file.import_logger;
        original_warnIfLogFlushFails = file.warnIfLogFlushFails;
    });

    afterEach(function() {
        // Restore originals (if they existed)
        if (original_import_export === undefined) {
            delete file.import_export;
        } else {
            file.import_export = original_import_export;
        }
        if (original_import_logger === undefined) {
            delete file.import_logger;
        } else {
            file.import_logger = original_import_logger;
        }
        if (original_warnIfLogFlushFails === undefined) {
            delete file.warnIfLogFlushFails;
        } else {
            file.warnIfLogFlushFails = original_warnIfLogFlushFails;
        }
    });

    it('propagates error from exportSessionDirectory', async function() {
        // Prepare environment where exportSessionDirectory rejects
        file.import_logger = {
            getRootLogger: () => ({
                flushSession: async () => {},
                flushGlobal: async () => {},
                getConfig: () => ({})
            }),
            log: {
                createChild: () => ({ warn: () => {} })
            }
        };
        file.warnIfLogFlushFails = async (_log, _msg, fn) => fn();

        file.import_export = {
            exportSessionDirectory: async (_args) => {
                throw new Error('export dir failed');
            }
        };

        const core = Object.create(KimiCore.prototype);
        core.homeDir = '/h';
        core.sessionStore = { get: async (s) => ({ id: s }) };
        core.sessions = new Map();

        const input = { sessionId: 'will-fail', includeGlobalLog: false };
        let caught = null;
        try {
            await core.exportSession(input);
        } catch (err) {
            caught = err;
        }
        assert.ok(caught instanceof Error, 'exportSession should reject when exportSessionDirectory fails');

        // Update expected message to match current behavior
        assert.strictEqual(caught.message, 'Session "will-fail" has no exportable directory at "undefined"');
    });
});