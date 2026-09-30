let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0001.useWorkspaceState', function() {
    // helper to recursively freeze an object so attempts to mutate will throw in strict mode
    function deepFreeze(obj) {
        if (obj === null || typeof obj !== 'object' || Object.isFrozen(obj)) return obj;
        Object.freeze(obj);
        Object.getOwnPropertyNames(obj).forEach(function(prop) {
            try {
                deepFreeze(obj[prop]);
            } catch (e) {
                // ignore non-freezable properties
            }
        });
        return obj;
    }

    it('should be exported and be a function', function() {
        assert.ok(testpilot_subject, 'module exported');
        assert.ok(testpilot_subject.file_0001, 'file_0001 exported');
        assert.strictEqual(typeof testpilot_subject.file_0001.useWorkspaceState, 'function',
            'useWorkspaceState should be a function');
    });

    })