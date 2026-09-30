let mocha = require('mocha');
let assert = require('assert');
let fs = require('fs');
let os = require('os');
let path = require('path');
let EventEmitter = require('events');

let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // increase timeout in case of slow CI
    this.timeout(5000);

    let child_process = require('child_process');
    let originalSpawn = child_process.spawn;

    afterEach(() => {
        // restore spawn after each test to avoid cross-test interference
        child_process.spawn = originalSpawn;
    });

    it('calls spawn with the provided rg binary and cwd', async function() {
        let captured = {};
        // create a fake child process that will emit some stdout then exit
        function makeFakeChild(stdoutChunks) {
            let cp = new EventEmitter();
            cp.stdout = new EventEmitter();
            cp.stderr = new EventEmitter();
            cp.kill = () => {}; // no-op
            // schedule data + exit on next tick so the caller can attach listeners
            setImmediate(() => {
                stdoutChunks.forEach(chunk => cp.stdout.em)})}    })
})