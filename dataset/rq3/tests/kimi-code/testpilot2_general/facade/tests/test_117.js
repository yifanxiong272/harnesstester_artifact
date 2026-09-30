let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Keep originals to restore after tests
    const originalSetTimeout = global.setTimeout;
    const originalClearTimeout = global.clearTimeout;

    afterEach(function() {
        // restore any globals we changed
        global.setTimeout = originalSetTimeout;
        global.clearTimeout = originalClearTimeout;
    });

    it('should have startDetachHintTimer on the prototype and be a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003, 'file_0003 namespace should exist');
        const proto = testpilot_subject.file_0003.ToolCallComponent &&
                      testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert.ok(proto, 'ToolCallComponent.prototype must exist');
        assert.strictEqual(typeof proto.startDetachHintTimer, 'function',
            'startDetachHintTimer should be a function on the prototype');
    });

    })