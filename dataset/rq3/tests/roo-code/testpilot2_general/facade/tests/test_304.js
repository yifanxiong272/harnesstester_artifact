let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to create a bare instance that uses the prototype method without running any constructor logic.
    function makeProcessorWithOptions(options) {
        const proto = testpilot_subject.file_0007.MessageProcessor.prototype;
        const inst = Object.create(proto);
        inst.options = options || {};
        return inst;
    }

    // Try to find an accessible reference to the module/object that provides debugLog.
    // In the original source the call is (0, import_cli.debugLog)(...), so the variable import_cli
    // may or may not be exposed on the exported module. We try a couple of likely locations.
    function findImportCli() {
        const m = testpilot_subject.file_0007;
        if (!m) return null;
        return m.import_cli || m.__import_cli || m._import_cli || null;
    }

    describe('testpilot_subject.file_0007.MessageProcessor.prototype.handleAction', function() {
        it('does not throw and returns undefined when debug is false or absent', function() {
            const mp = makeProcessorWithOptions({ debug: false });
            const message = { action: 'do-something' };
            const result = mp.handleAction(message);
            assert.strictEqual(result, undefined);
        });

            })
})