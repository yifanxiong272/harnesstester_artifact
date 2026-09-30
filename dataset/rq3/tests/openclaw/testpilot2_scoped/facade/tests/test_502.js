let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.resolveBootstrapWarningSignaturesSeen', function() {
    const fn = testpilot_subject.file_0017.resolveBootstrapWarningSignaturesSeen;

    it('returns warningSignaturesSeen from the report when present (array case)', function() {
        const report = {
            bootstrapTruncation: {
                warningSignaturesSeen: ['sigA', 'sigB']
            }
        };
        const res = fn(report);
        assert.deepStrictEqual(res, ['sigA', 'sigB']);
    });

    })