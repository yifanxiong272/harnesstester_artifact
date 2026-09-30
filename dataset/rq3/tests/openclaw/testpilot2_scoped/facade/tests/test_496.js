let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    it('includes warningSignaturesSeen when warning.warningSignaturesSeen is non-empty', function() {
        const params = {
            warningMode: 'soft',
            warning: {
                warningShown: true,
                signature: 'prompt-sig-123',
                warningSignaturesSeen: ['sig-A', 'sig-B']
            },
            analysis: {
                truncatedFiles: ['file1.txt', 'file2.txt'],
                nearLimitFiles: ['file3.txt'],
                totalNearLimit: 7
            }
        };

        const meta = testpilot_subject.file_0017.buildBootstrapTruncationReportMeta(params);

        const expected = {
            warningMode: 'soft',
            warningShown: true,
            promptWarningSignature: 'prompt-sig-123',
            warningSignaturesSeen: ['sig-A', 'sig-B'],
            truncatedFiles: 2,
            nearLimitFiles: 1,
            totalNearLimit: 7
        };

        assert.deepStrictEqual(meta, expected);
    });

    })