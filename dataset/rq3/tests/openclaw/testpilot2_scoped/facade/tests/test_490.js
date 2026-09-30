let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.buildBootstrapInjectionStats', function() {
    const build = testpilot_subject &&
                  testpilot_subject.file_0017 &&
                  testpilot_subject.file_0017.buildBootstrapInjectionStats;

    it('exists and is a function', function() {
        assert.ok(build, 'buildBootstrapInjectionStats should be present');
        assert.strictEqual(typeof build, 'function', 'buildBootstrapInjectionStats should be a function');
    });

    })