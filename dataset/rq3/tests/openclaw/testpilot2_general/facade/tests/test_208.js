let mocha = require('mocha');
let assert = require('assert');
let EventEmitter = require('events').EventEmitter;

// Helper to load the module with a provided fake 'net' implementation
function loadWithFakeNet(fakeNet) {
    // Monkey-patch the core 'net' module's createConnection so that when
    // 'testpilot_subject' requires it, the fake implementation is used.
    const net = require('net');
    const origCreateConnection = net.createConnection;

    // Replace createConnection
    net.createConnection = fakeNet.createConnection;

    // Ensure the module is reloaded (so it picks up our patched net)
    delete require.cache[require.resolve('testpilot_subject')];

    try {
        return require('..');
    } finally {
        // Restore original implementation so other tests aren't affected.
        net.createConnection = origCreateConnection;
    }
}

describe('test testpilot_subject', function() {
    it('resolves when underlying socket emits "connect" and passes host/port to net.createConnection', async function() {
        let capturedArgs = null;

        let fakeNet = {
            createConnection: function() {
                capturedArgs = Array.prototype.slice.call(arguments);
                let sock = new EventEmitter();
                sock.write = function() {};
                sock.end = function() {};
                sock.destroy = function() {};
                // Emit 'connect' on next tick to simulate successful connection
                process.nextTick(() => {
                    sock.em})}}    })
})