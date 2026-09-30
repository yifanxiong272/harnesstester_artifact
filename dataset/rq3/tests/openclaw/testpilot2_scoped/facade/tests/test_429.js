let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');

let testpilot_subject = require('..');

describe('test testpilot_subject.file_0015.installCompletion', function() {
    // keep a copy of originals to restore later
    const origConsoleError = console.error;
    const origConsoleLog = console.log;
    const origConsoleWarn = console.warn;
    const origHome = process.env.HOME;

    let capturedErrors;
    let capturedLogs;
    let capturedWarns;
    let tmpHomeDir;

    beforeEach(function() {
        // create a temporary HOME directory for isolation
        tmpHomeDir = fs.mkdtempSync(path.join(os.tmpdir(), 'testpilot_home_'));
        process.env.HOME = tmpHomeDir;

        capturedErrors = [];
        capturedLogs = [];
        capturedWarns = [];

        console.error = function() {
            capturedErrors.push(Array.from(arguments).join(' '));
        };
        console.log = function() {
            capturedLogs.push(Array.from(arguments).join(' '));
        };
        console.warn = function() {
            capturedWarns.push(Array.from(arguments).join(' '));
        };
    });

    afterEach(function() {
        // restore console and HOME
        console.error = origConsoleError;
        console.log = origConsoleLog;
        console.warn = origConsoleWarn;
        process.env.HOME = origHome;

        // cleanup tmpHomeDir
        try {
            // remove created files/directories if any (safe best-effort)
            fs.rmdirSync(tmpHomeDir, { recursive: true });
        } catch (e) {
            // ignore
        }
    });

    it('reports missing completion cache for a supported shell without accessing external files', async function() {
        // Use a supported shell (zsh) but do not create any cache state.
        // The function should detect missing cache and error out with a helpful message.
        await testpilot_subject.file_0015.installCompletion('zsh', false, 'mycli');

        // It should have produced an error indicating the cache is not found
        assert.ok(
            capturedErrors.some(e => e.includes('Completion cache not found')),
            'expected an error message indicating the completion cache was not found'
        );

        // Also expect the error message to suggest running the write-state command with our binName
        assert.ok(
            capturedErrors.some(e => e.includes('Run `mycli completion --write-state` first.')),
            'expected a hint to run `mycli completion --write-state`'
        );

        // No warnings or success logs expected for this early-exit path
        assert.strictEqual(capturedWarns.length, 0);
    });

    })