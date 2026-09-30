let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const subject = testpilot_subject.file_0001;
    if (!subject || typeof subject.isFailoverErrorMessage !== 'function') {
        throw new Error('testpilot_subject.file_0001.isFailoverErrorMessage not found');
    }

    let origClassify;

    beforeEach(function() {
        // Save original so we can restore after each test
        origClassify = subject.classifyFailoverReason;
    });

    afterEach(function() {
        // Restore original implementation to avoid test cross-talk
        subject.classifyFailoverReason = origClassify;
    });

    it('returns false when classifyFailoverReason returns null', function() {
        // Arrange: stub classifyFailoverReason to return null for the supplied raw input
        subject.classifyFailoverReason = function(raw) {
            // verify the raw value is forwarded through
            assert.strictEqual(raw, 'not-a-failover');
            return null;
        };

        // Act & Assert
        assert.strictEqual(subject.isFailoverErrorMessage('not-a-failover'), false);
    });

    })