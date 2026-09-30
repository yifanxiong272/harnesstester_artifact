let mocha = require('mocha');
let assert = require('assert');
let stream = require('stream');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout in case environment is slow
    this.timeout(5000);

    function makePromptManager() {
        let pm = new testpilot_subject.file_0004.PromptManager();
        return pm;
    }

    it('promptForInput resolves with the entered text and calls hooks (afterPrompt called twice)', function() {
        let pm = makePromptManager();

        // Create controllable stdin/stdout streams
        let stdin = new stream.Readable({
            read() {} // we'll push data manually
        });
        let capturedOut = '';
        let stdout = new stream.Writable({
            write(chunk, encoding, callback) {
                capturedOut += chunk.toString();
                callback();
            }
        });

        pm.stdin = stdin;
        pm.stdout = stdout;

        let beforeCalled = 0;
        let afterCalled = 0;
        pm.beforePrompt = function() { beforeCalled++; };
        pm.afterPrompt = function() { afterCalled++; };

        // Start prompting
        let p = pm.promptForInput('Enter: ');

        // Simulate user typing after a short delay
        setTimeout(() => {
            stdin.push('my answer\n');
        }, 5);

        return p.then(answer => {
            assert.strictEqual(answer, 'my answer');
            // readline.question writes the prompt to stdout
            assert.strictEqual(capturedOut, 'Enter: ');
            // beforePrompt should be called once
            assert.strictEqual(beforeCalled, 1);
            // afterPrompt is expected to be called twice:
            // once directly in the question callback and once via the 'close' event handler
            assert.strictEqual(afterCalled, 2);
            // isPrompting should be false after completion
            assert.strictEqual(pm.isPrompting, false);
        });
    });

    })