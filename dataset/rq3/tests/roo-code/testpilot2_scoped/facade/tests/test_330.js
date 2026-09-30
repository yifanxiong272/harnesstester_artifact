let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to find a method name on an object from a list of candidates
    function findMethod(obj, candidates) {
        for (let name of candidates) {
            if (typeof obj[name] === 'function') return name;
        }
        return null;
    }

    // helper to find an array-like property on the object we can mutate
    function findArrayProperty(obj) {
        for (let key of Object.keys(obj)) {
            try {
                if (Array.isArray(obj[key])) return key;
            } catch (e) {
                // ignore getters that throw
            }
        }
        return null;
    }

    it('isEmpty should be a function and return a boolean for a new instance', function() {
        let Service = testpilot_subject.file_0012.MessageQueueService;
        assert.strictEqual(typeof Service, 'function', 'MessageQueueService should be a constructor');

        let svc = new Service();
        assert.strictEqual(typeof svc.isEmpty, 'function', 'instance should have isEmpty method');

        let val = svc.isEmpty();
        assert.strictEqual(typeof val, 'boolean', 'isEmpty() should return a boolean');
    });

    })