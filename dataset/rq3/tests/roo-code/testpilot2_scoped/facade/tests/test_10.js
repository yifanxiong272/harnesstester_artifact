let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Save and restore any existing global.currentMinComponentLines to avoid side effects
    let savedGlobalValue;
    beforeEach(function() {
        savedGlobalValue = Object.prototype.hasOwnProperty.call(global, 'currentMinComponentLines')
            ? global.currentMinComponentLines
            : undefined;
        // Ensure a clean starting state for each test
        delete global.currentMinComponentLines;
    });

    afterEach(function() {
        if (savedGlobalValue === undefined) {
            delete global.currentMinComponentLines;
        } else {
            global.currentMinComponentLines = savedGlobalValue;
        }
    });

    it('exposes file_0003.setMinComponentLines as a function', function() {
        assert.ok(testpilot_subject);
        assert.ok(testpilot_subject.file_0003);
        assert.strictEqual(typeof testpilot_subject.file_0003.setMinComponentLines, 'function');
    });

    })