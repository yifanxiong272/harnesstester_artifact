let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0001.OpenAiCodexOAuthManager.prototype;
    let originalConsoleLog;

    beforeEach(function() {
        // Save original console.log so tests can stub it
        originalConsoleLog = console.log;
    });

    afterEach(function() {
        // Restore original console.log after each test
        console.log = originalConsoleLog;
    });

    it('calls provided logFn with the message (and does not call console.log)', function() {
        const manager = Object.create(proto);

        // capture calls to logFn
        let captured = null;
        manager.logFn = function(msg) { captured = msg; };

        // Make sure console.log would fail the test if called
        console.log = function() { throw new Error('console.log should not be called when logFn is present'); };

        manager.log('hello world');

        assert.strictEqual(captured, 'hello world');
    });

    })