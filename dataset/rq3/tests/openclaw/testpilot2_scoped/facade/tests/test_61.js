let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subj = testpilot_subject.file_0001;
    let origIsLikely;

    before(function() {
        // save original (may be undefined)
        origIsLikely = subj.isLikelyContextOverflowError;
    });

    after(function() {
        // restore
        if (typeof origIsLikely !== 'undefined') {
            subj.isLikelyContextOverflowError = origIsLikely;
        } else {
            delete subj.isLikelyContextOverflowError;
        }
    });

    it('returns false for falsy errorMessage values', function(done) {
        assert.strictEqual(subj.isCompactionFailureError(null), false);
        assert.strictEqual(subj.isCompactionFailureError(undefined), false);
        assert.strictEqual(subj.isCompactionFailureError(''), false);
        done();
    });

    })