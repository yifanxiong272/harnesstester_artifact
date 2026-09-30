let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // locate the class under test
    const OMClass = testpilot_subject &&
                    testpilot_subject.file_0002 &&
                    testpilot_subject.file_0002.OutputManager;

    // helper that attempts to create a real instance but falls back to a prototype-bound object
    function makeInstance() {
        if (typeof OMClass !== 'function') {
            // If the class is missing, return a plain object so tests fail clearly on existence check below.
            return {};
        }
        try {
            return new OMClass();
        } catch (e) {
            // Some constructors require arguments or environment; fall back to an object whose prototype
            // is OutputManager.prototype so we can still exercise the output method safely.
            return Object.create(OMClass.prototype);
        }
    }

    it('OutputManager class should exist and have an output method on its prototype', function() {
        assert.ok(typeof OMClass === 'function', 'OutputManager constructor should be a function');
        assert.ok(typeof OMClass.prototype.output === 'function', 'OutputManager.prototype.output should be a function');
    });

    })