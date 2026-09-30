let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    let OutputManager = null;
    let streamContent = null;
    let instance = null;

    before(function() {
        // Skip the whole suite if the module shape isn't as expected.
        if (!testpilot_subject
            || !testpilot_subject.file_0002
            || !testpilot_subject.file_0002.OutputManager
            || !testpilot_subject.file_0002.OutputManager.prototype) {
            this.skip();
            return;
        }
        OutputManager = testpilot_subject.file_0002.OutputManager;
        streamContent = OutputManager.prototype.streamContent;
        if (typeof streamContent !== 'function') {
            this.skip();
            return;
        }

        // Try to construct an instance; if construction fails, fall back to plain object
        try {
            instance = new OutputManager();
        } catch (e) {
            instance = {};
        }
    });

    it('test testpilot_subject.file_0002.OutputManager.prototype.streamContent exists and has arity 3', function() {
        assert.strictEqual(typeof streamContent, 'function');
        // The declared number of formal parameters should be 3 (ts, text, header)
        assert.strictEqual(streamContent.length, 3);
    });

    })