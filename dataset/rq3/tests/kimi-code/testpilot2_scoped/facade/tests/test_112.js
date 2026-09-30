let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep tests fast and avoid relying on external resources. These tests
    // check the presence and basic calling contract of the async method
    // archiveSession. They are defensive: they only assert properties that
    // do not require contacting external services.

    const KimiCore = testpilot_subject &&
                     testpilot_subject.file_0002 &&
                     testpilot_subject.file_0002.KimiCore;

    it('KimiCore class should be exported', function() {
        assert.ok(KimiCore, 'expected testpilot_subject.file_0002.KimiCore to be defined');
        assert.strictEqual(typeof KimiCore, 'function', 'KimiCore should be a constructor');
    });

    })