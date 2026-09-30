let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.buildBootstrapTruncationReportMeta', function() {
    const fn = testpilot_subject &&
               testpilot_subject.file_0017 &&
               testpilot_subject.file_0017.buildBootstrapTruncationReportMeta;

    it('should export a function', function() {
        assert.ok(typeof fn === 'function', 'buildBootstrapTruncationReportMeta should be a function');
    });

    })