let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const promptFn = testpilot_subject.file_0002.KimiCore.prototype.prompt;

    it('should call sessionApi with sessionId and pass payload excluding sessionId', function() {
        let instance = {
            calledWith: undefined,
            receivedPayload: undefined,
            sessionApi(sessionId) {
                this.calledWith = sessionId;
                return {
                    prompt: (payload) => {
                        this.receivedPayload = payload;
                        return 'returned-value';
                    }
                };
            }
        };

        const input = { sessionId: 'mysession', alpha: 1, beta: 'two' };
        const result = promptFn.call(instance, input);

        assert.strictEqual(result, 'returned-value');
        assert.strictEqual(instance.calledWith, 'mysession');
        assert.deepStrictEqual(instance.receivedPayload, { alpha: 1, beta: 'two' });
    });

    })