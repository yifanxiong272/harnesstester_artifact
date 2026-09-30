let mocha = require('mocha');
let assert = require('assert');
let EventEmitter = require('events').EventEmitter;
let Module = require('module');

// Try to require 'proxyquire' if available; otherwise provide a minimal in-test fallback.
// The fallback implements only the subset used by this test: proxyquire.noCallThru().load(path, stubs)
let proxyquire;
try {
    proxyquire = require('proxyquire');
} catch (err) {
    proxyquire = {
        noCallThru: function() {
            return {
                load: function(requestPath, stubs) {
                    // Temporarily override Module._load to return stubbed modules when requested.
                    const originalLoad = Module._load;
                    Module._load = function(request, parent, isMain) {
                        if (stubs && Object.prototype.hasOwnProperty.call(stubs, request)) {
                            return stubs[request];
                        }
                        return originalLoad.apply(this, arguments);
                    };

                    // Clear any cached copy of the target module so it gets loaded fresh
                    try {
                        delete require.cache[require.resolve(requestPath)];
                    } catch (_) {}

                    try {
                        return require(requestPath);
                    } finally {
                        // Restore original loader
                        Module._load = originalLoad;
                    }
                }
            };
        }
    };
}

describe('test testpilot_subject', function() {
    // Helper to load the module with a provided fake 'net' implementation
    function loadWithFakeNet(fakeNet) {
        // Ensure proxyquire does not call through to the real 'net' module
        return proxyquire.noCallThru().load('testpilot_subject', {
            net: fakeNet
        });
    }

    it('rejects when underlying socket emits "error"', async function() {
        let fakeNet = {
            createConnection: function() {
                let sock = new EventEmitter();
                sock.write = function() {};
                sock.end = function() {};
                sock.destroy = function() {};
                // Emit 'error' on next tick to simulate connection error
                process.nextTick(() => {
                    sock.em})}}    })
})