let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0003.ToolCallComponent.prototype.stopStreamingProgressTimer', function() {
        let origClearInterval;
        let origClearTimeout;
        let calls;

        beforeEach(function() {
            // backup originals
            origClearInterval = global.clearInterval;
            origClearTimeout = global.clearTimeout;
            calls = [];

            // spy replacements that record calls
            global.clearInterval = function(id) {
                calls.push({type: 'interval', id: id});
            };
            global.clearTimeout = function(id) {
                calls.push({type: 'timeout', id: id});
            };
        });

        afterEach(function() {
            // restore originals
            global.clearInterval = origClearInterval;
            global.clearTimeout = origClearTimeout;
        });

        it('clears an existing streamingProgressTimer (calls clearInterval/clearTimeout) and nullifies the property', function() {
            // create a bare instance using the prototype so we don't depend on constructor behavior
            let component = Object.create(testpilot_subject.file_0003.ToolCallComponent.prototype);

            // set a fake timer id
            component.streamingProgressTimer = 12345;

            // call the method under test
            component.stopStreamingProgressTimer();

            // One of clearInterval or clearTimeout should have been called with the id we set
            assert.strictEqual(calls.length, 1, 'expected exactly one clear* call');
            assert.strictEqual(calls[0].id, 12345, 'expected clear* to be called with the timer id we set');

            // The streamingProgressTimer property should be cleared / falsy after the call
            assert.ok(!component.streamingProgressTimer, 'expected streamingProgressTimer to be falsy after stopping');
        });

            })
})