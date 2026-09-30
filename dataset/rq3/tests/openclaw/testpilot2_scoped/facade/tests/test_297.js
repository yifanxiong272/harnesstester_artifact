let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('exports createSubsystemRuntime and has expected arity', function() {
        assert.ok(testpilot_subject, 'module should be present');
        assert.ok(testpilot_subject.file_0011, 'file_0011 namespace should be present');
        let fn = testpilot_subject.file_0011.createSubsystemRuntime;
        assert.ok(fn, 'createSubsystemRuntime should be exported');
        assert.strictEqual(typeof fn, 'function', 'createSubsystemRuntime should be a function');
        // Most likely signature is (subsystem, exit). Ensure it accepts two declared params.
        assert.ok(fn.length >= 1, 'createSubsystemRuntime should accept at least one parameter');
        // Some implementations default the exit param, so it may declare 1 or 2 args. We only assert >=1.
    });

    })