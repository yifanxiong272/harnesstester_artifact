let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const processResponsesApiStream = testpilot_subject.file_0019.processResponsesApiStream;

    // helper to turn an array into an async iterable stream
    function streamFromArray(arr) {
        return (async function* () {
            for (const e of arr) {
                // yield asynchronously to simulate real streams
                await new Promise((r) => setImmediate(r));
                yield e;
            }
        })();
    }

    // helper to collect all values from an async generator
    async function collect(gen) {
        const out = [];
        for await (const v of gen) out.push(v);
        return out;
    }

    it('yields text deltas for response.output_text.delta and response.text.delta', async function() {
        const events = [
            { type: "response.output_text.delta", delta: "hello" },
            { type: "response.text.delta", delta: " world" }
        ];
        const stream = streamFromArray(events);
        const gen = processResponsesApiStream(stream, () => null);
        const out = await collect(gen);
        assert.deepStrictEqual(out, [
            { type: "text", text: "hello" },
            { type: "text", text: " world" }
        ]);
    });

    })