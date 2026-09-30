let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const procFn = testpilot_subject.file_0007.MessageProcessor.prototype.processMessages;

    it('calls processMessage for every message in the array', function(done) {
        const seen = [];
        const obj = {
            processMessage: function(message) {
                seen.push(message);
            }
        };

        const messages = ['m1', 'm2', 'm3'];
        const ret = procFn.call(obj, messages);

        // processMessages does not return anything (undefined)
        assert.strictEqual(ret, undefined);
        assert.deepStrictEqual(seen, messages);
        done();
    });

    })