let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0017.analyzeBootstrapBudget', function() {
    const fn = testpilot_subject.file_0017.analyzeBootstrapBudget;

    it('handles a missing file: sums should ignore missing files and file augmented correctly', function() {
        const params = {
            bootstrapMaxChars: 100,
            bootstrapTotalMaxChars: 200,
            nearLimitRatio: 0.8,
            files: [
                { name: 'missing-file', missing: true }
            ]
        };

        const res = fn(params);

        // Totals: non-missing files are zero
        assert.strictEqual(res.totals.rawChars, 0);
        assert.strictEqual(res.totals.injectedChars, 0);
        assert.strictEqual(res.totals.truncatedChars, 0);

        // File was preserved but augmented
        assert.strictEqual(res.files.length, 1);
        assert.strictEqual(res.files[0].name, 'missing-file');
        assert.strictEqual(res.files[0].missing, true);
        assert.strictEqual(res.files[0].nearLimit, false);
        assert.deepStrictEqual(res.files[0].causes, []);

        // No truncation reported
        assert.strictEqual(res.truncatedFiles.length, 0);
        assert.strictEqual(res.hasTruncation, false);
    });

    })