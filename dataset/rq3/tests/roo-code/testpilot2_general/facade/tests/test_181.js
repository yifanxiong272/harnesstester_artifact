let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase default Mocha timeout a bit in case of slow CI environment
    this.timeout(5000);

    it('promptForYesNoWithTimeout resolves true when user inputs "y" before timeout', async function() {
        const PromptManager = testpilot_subject.file_0004.PromptManager;
        const pm = new PromptManager();

        // Start the prompt; it should be listening for stdin data
        const promise = pm.promptForYesNoWithTimeout('Proceed?', 1000, false);

        // Simulate a user typing 'y' (with newline) shortly after the prompt starts
        setTimeout(() => {
            process.stdin.em})    })
})