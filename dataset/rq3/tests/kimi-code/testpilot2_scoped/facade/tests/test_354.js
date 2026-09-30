let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const KimiCore = testpilot_subject && testpilot_subject.file_0002 && testpilot_subject.file_0002.KimiCore;

    it('exports KimiCore (constructor/function) from testpilot_subject.file_0002', function() {
        assert.ok(typeof KimiCore === 'function', 'KimiCore should be a function (constructor)');
    });

    })