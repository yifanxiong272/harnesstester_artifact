let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.detectCursorKeyMode', function() {
    const detect = testpilot_subject.file_0009.detectCursorKeyMode;

    it('returns null when neither SMKX nor RMKX are present', function() {
        const raw = 'some random data without tokens';
        assert.strictEqual(detect(raw), null);
    });

    })