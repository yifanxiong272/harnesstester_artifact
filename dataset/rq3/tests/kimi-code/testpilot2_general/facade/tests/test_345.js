let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase timeout for timers just in case
    this.timeout(5000);

    // Minimal mock socket used by WsConnection
    function makeMockSocket() {
        const sock = {
            OPEN: 1,
            readyState: 1,
            sent: [],
            handlers: {},
            send(data, cb) {
                // Record the raw data (string)
                this.sent.push(data);
                if (typeof cb === 'function') {
                    // emulate async callback but call synchronously
                    try { cb(); } catch (e) { /* ignore */ }
                }
            },
            on(name, fn) {
                this.handlers[name] = fn;
            },
            terminateCalled: false,
            terminate() { this.terminateCalled = true; },
            closeCalled: false,
            close(code, reason) { this.closeCalled = true; this.readyState = 0; if (this.handlers['close']) this.handlers['close'](code, reason); }
        };
        return sock;
    }

    // Minimal logger stub
    function makeLogger() {
        const messages = { warn: [], info: [] };
        const logger = {
            child() { return logger; },
            warn(obj, msg) { messages.warn.push({ obj, msg }); },
            info(obj, msg) { messages.info.push({ obj, msg }); },
            _messages: messages
        };
        return logger;
    }

    it('constructor sends a server_hello message (contains ws_connection_id)', function() {
        const socket = makeMockSocket();
        const logger = makeLogger();
        // minimal sessionClients and wsBroadcast not used here
        const sessionClients = {
            subscribe() {}, unsubscribe() {}, forgetConnection() {}
        };
        const wsBroadcast = {};
        const conn = new testpilot_subject.file_0006.WsConnection({
            remoteAddress: '1.2.3.4',
            userAgent: 'mocha-test',
            socket,
            logger,
            sessionClients,
            wsBroadcast,
            // make ping large to reduce timer activity during test
            pingIntervalMs: 1000000
        });

        // Constructor should have sent exactly one message (server_hello)
        assert.strictEqual(socket.sent.length, 1, 'expected one initial send (server_hello)');
        const parsed = JSON.parse(socket.sent[0]);
        // server hello builder includes ws_connection_id; ensure it's present and looks like conn_*
        assert.ok(parsed.ws_connection_id || (parsed.payload && parsed.payload.ws_connection_id), 'server hello should include ws_connection_id');
        const idVal = parsed.ws_connection_id ?? parsed.payload.ws_connection_id;
        assert.strictEqual(typeof idVal, 'string');
        assert.ok(idVal.startsWith('conn_'), 'ws_connection_id should start with "conn_"');
        // cleanup timers
        conn.onClose(1000, 'test done');
    });

    })