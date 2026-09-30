let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const proto = testpilot_subject.file_0016.FakeAIHandler.prototype;

    it('delegates all yielded values from ai.createMessage (basic sequence)', async function() {
        const handler = Object.create(proto);
        handler.ai = {
            async *createMessage(systemPrompt, messages, metadata) {
                yield 'first';
                yield 'second';
                yield 'third';
            }
        };

        const seen = [];
        for await (const v of handler.createMessage('S', ['m'], {x: 1})) {
            seen.push(v);
        }

        assert.deepStrictEqual(seen, ['first', 'second', 'third']);
    });

    })