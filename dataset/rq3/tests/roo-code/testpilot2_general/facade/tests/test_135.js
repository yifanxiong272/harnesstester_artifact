let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Helper to get size of a set-like container in a robust way
    function getSize(container) {
        if (container == null) return undefined;
        if (typeof container.size === 'number') return container.size;
        if (typeof container.length === 'number') return container.length;
        try {
            // If it's iterable, convert to array
            return Array.from(container).length;
        } catch (e) {
            return undefined;
        }
    }

    // Helper to test membership robustly (supports Set-like and Array-like)
    function contains(container, value) {
        if (container == null) return false;
        if (typeof container.has === 'function') return container.has(value);
        if (Array.isArray(container) || typeof container.includes === 'function') return container.includes(value);
        try {
            return Array.from(container).some(x => x === value);
        } catch (e) {
            return false;
        }
    }

    it('should expose OutputManager class', function() {
        assert.ok(testpilot_subject.file_0002, "file_0002 namespace missing");
        assert.ok(typeof testpilot_subject.file_0002.OutputManager === 'function', "OutputManager constructor missing");
    });

    })