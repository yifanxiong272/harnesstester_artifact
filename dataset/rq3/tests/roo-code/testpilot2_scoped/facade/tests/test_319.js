let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper: try several common ways to add a message into a MessageQueueService instance.
    function addMessageToService(svc, msg) {
        // Try common method names first
        const tryCall = (name, arg) => {
            if (typeof svc[name] === 'function') {
                try {
                    svc[name](arg);
                    return true;
                } catch (e) {
                    // ignore and continue trying other ways
                }
            }
            return false;
        };

        if (tryCall('enqueue', msg)) return;
        if (tryCall('add', msg)) return;
        if (tryCall('push', msg)) return;
        if (tryCall('offer', msg)) return;
        if (tryCall('put', msg)) return;

        // Try common internal storage shapes
        try {
            if (Array.isArray(svc.messages)) {
                svc.messages.push(msg);
                return;
            }
        } catch (e) {}

        try {
            if (Array.isArray(svc._messages)) {
                svc._messages.push(msg);
                return;
            }
        } catch (e) {}

        try {
            if (Array.isArray(svc.queue)) {
                svc.queue.push(msg);
                return;
            }
        } catch (e) {}

        try {
            if (Array.isArray(svc._queue)) {
                svc._queue.push(msg);
                return;
            }
        } catch (e) {}

        // If it uses a map-like object keyed by id
        try {
            if (svc.messages == null) svc.messages = {};
            if (typeof svc.messages === 'object' && !Array.isArray(svc.messages)) {
                svc.messages[msg.id] = msg;
                return;
            }
        } catch (e) {}

        try {
            if (svc._messages == null) svc._messages = {};
            if (typeof svc._messages === 'object' && !Array.isArray(svc._messages)) {
                svc._messages[msg.id] = msg;
                return;
            }
        } catch (e) {}

        // Fallback: attach a property that many find implementations might scan
        try {
            svc.__test_messages = svc.__test_messages || [];
            svc.__test_messages.push(msg);
        } catch (e) {
            // last resort: set a property by id
            svc[msg.id] = msg;
        }
    }

    it('has findMessage on the prototype and it is a function', function(done) {
        assert.ok(testpilot_subject.file_0012, 'module should expose file_0012');
        const Service = testpilot_subject.file_0012.MessageQueueService;
        assert.ok(Service, 'MessageQueueService should be exported');
        assert.strictEqual(typeof Service.prototype.findMessage, 'function', 'findMessage should be a function on the prototype');
        done();
    });

    })