let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to call updateMessage and normalize synchronous/promise results
    function runUpdate(service, id, text, images) {
        return new Promise((resolve, reject) => {
            try {
                let result = service.updateMessage(id, text, images);
                if (result && typeof result.then === 'function') {
                    // It's a promise-like
                    result.then(resolve).catch(reject);
                } else {
                    // Synchronous result
                    resolve(result);
                }
            } catch (err) {
                reject(err);
            }
        });
    }

    it('test testpilot_subject.file_0012.MessageQueueService.prototype.updateMessage exists', function() {
        assert.ok(testpilot_subject.file_0012, 'file_0012 namespace should exist on module');
        let Service = testpilot_subject.file_0012.MessageQueueService;
        assert.ok(Service, 'MessageQueueService should be exported');
        let service = (typeof Service === 'function') ? new Service() : Service;
        assert.strictEqual(typeof service.updateMessage, 'function', 'updateMessage should be a function');
    });

    })