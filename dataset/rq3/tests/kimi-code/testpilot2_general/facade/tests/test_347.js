let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject.file_0006.WsConnection.prototype.onMessage', function() {
    // Grab the function so we can call it with a fake `this`.
    const onMessage = testpilot_subject.file_0006.WsConnection.prototype.onMessage;

    function makeMockThis() {
        const warned = [];
        return {
            closed: false,
            logger: {
                warn: function() {
                    // capture all args to allow flexible assertions
                    warned.push(Array.from(arguments));
                }
            },
            // default no-op handlers (some may be replaced per-test)
            onClientHello: async function() {},
            onPong: function() {},
            onSubscribe: async function() {},
            onUnsubscribe: function() {},
            onAbort: function() {},
            onWatchFsAdd: function() {},
            onWatchFsRemove: function() {},
            onTerminalAttach: function() {},
            onTerminalDetach: function() {},
            onTerminalInput: function() {},
            onTerminalResize: function() {},
            onTerminalClose: function() {},
            _warned: warned,
        };
    }

    it('ignores non-json frames and logs a warning', function() {
        const mock = makeMockThis();
        // pass a Buffer that is not valid JSON
        const data = Buffer.from("this is not json");
        onMessage.call(mock, data);
        assert(mock._warned.length >= 1, "expected at least one warning");
        // check that one of the warn calls includes the expected message
        const found = mock._warned.some(args => args.some(a => typeof a === 'string' && a.includes('non-json ws frame')));
        assert(found, "expected a 'non-json ws frame; ignoring' warning");
    });

    })