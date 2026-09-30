let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0007.MessageProcessor.prototype.emitStateChangeEvents', function() {
    // Keep originals so we can restore after tests
    let origImportEvents;
    let origImportCli;

    before(function() {
        // Ensure module structure exists
        assert.ok(testpilot_subject && testpilot_subject.file_0007, "testpilot_subject.file_0007 must exist");

        // Save originals (may be undefined, that's fine)
        origImportEvents = testpilot_subject.file_0007.import_events;
        origImportCli = testpilot_subject.file_0007.import_cli;

        // Provide a default import_events shape so tests can stub individual functions easily.
        if (!testpilot_subject.file_0007.import_events) {
            testpilot_subject.file_0007.import_events = {};
        }
        if (!testpilot_subject.file_0007.import_cli) {
            testpilot_subject.file_0007.import_cli = {};
        }
    });

    after(function() {
        // Restore originals
        testpilot_subject.file_0007.import_events = origImportEvents;
        testpilot_subject.file_0007.import_cli = origImportCli;
    });

    // Helper to create a "processor" object that uses the real prototype but controlled emitter/options
    function createProcessor() {
        const proto = testpilot_subject.file_0007.MessageProcessor.prototype;
        const proc = Object.create(proto);
        proc.emitter = {
            calls: [],
            emit: function(eventName, payload) {
                this.calls.push({ eventName, payload });
            }
        };
        // sensible defaults; tests will override as needed
        proc.options = { emitAllStateChanges: false, debug: false };
        return proc;
    }

    function findCall(emitter, name) {
        return emitter.calls.find(c => c.eventName === name);
    }

    it('does not emit "stateChange" when not significant and emitAllStateChanges is false, but does when emitAllStateChanges is true', function() {
        const proc = createProcessor();

        // Stub to not significant
        testpilot_subject.file_0007.import_events.isSignificantStateChange = (prev, cur) => false;

        const prev = { a: 1 };
        const cur = { a: 1 };

        // First: default emitAllStateChanges=false => no event
        proc.options.emitAllStateChanges = false;
        proc.emitStateChangeEvents.call(proc, prev, cur);
        assert.strictEqual(findCall(proc.emitter, "stateChange"), undefined, "should not emit stateChange when not significant and emitAllStateChanges=false");

        // Second: set emitAllStateChanges=true => should emit
        proc.emitter.calls = [];
        proc.options.emitAllStateChanges = true;
        proc.emitStateChangeEvents.call(proc, prev, cur);
        const call = findCall(proc.emitter, "stateChange");
        assert.ok(call, "expected stateChange event when emitAllStateChanges=true");
        assert.strictEqual(call.payload.isSignificantChange, false);
    });

    })