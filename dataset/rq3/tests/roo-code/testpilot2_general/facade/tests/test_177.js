let mocha = require('mocha');
let assert = require('assert');
let EventEmitter = require('events');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Ensure the helper used in the implementation exists (some builds wrap functions with __name)
    if (typeof global.__name === 'undefined') {
        global.__name = function(fn /*, name*/) { return fn; };
    }

    // Helper to create a fake PromptManager "this" context to call the prototype method with
    function createFakePromptManager(options = {}) {
        const stdin = new EventEmitter();
        stdin.isTTY = !!options.isTTY;
        // use a defined boolean for isRaw so that the code attempts to restore it
        stdin.isRaw = (typeof options.isRaw === 'boolean') ? options.isRaw : false;
        stdin.setRawMode = function(mode) {
            // record call and set isRaw accordingly
            stdin._setRawModeCalls = stdin._setRawModeCalls || [];
            stdin._setRawModeCalls.push(mode);
            stdin.isRaw = mode;
        };
        stdin.resume = function(){ stdin._resumed = true; };
        stdin.pause = function(){ stdin._paused = true; };

        const stdout = {
            buffer: '',
            write: function(chunk) {
                // coerce Buffer to string if necessary
                this.buffer += String(chunk);
            }
        };

        const calls = { before: 0, after: 0 };
        const fake = {
            stdin,
            stdout,
            isPrompting: false,
            beforePrompt: function(){ calls.before++; },
            afterPrompt: function(){ calls.after++; },
            __calls: calls
        };
        return fake;
    }

    // Convenience to call the method under test
    async function callPromptWithTimeout(fakeThis, prompt, timeoutMs, defaultValue) {
        // call the prototype method directly with our fakeThis
        return await testpilot_subject.file_0004.PromptManager.prototype.promptWithTimeout.call(fakeThis, prompt, timeoutMs, defaultValue);
    }

    it('resolves with typed input when Enter pressed before timeout', async function() {
        const pm = createFakePromptManager({ isTTY: true, isRaw: false });
        const prompt = 'Enter name: ';
        const timeoutMs = 200;
        const defaultValue = 'DEF';

        // start the prompt
        const promise = callPromptWithTimeout(pm, prompt, timeoutMs, defaultValue);

        // simulate typing "hello" and pressing Enter in next tick
        process.nextTick(() => {
            pm.stdin.em})    })
})