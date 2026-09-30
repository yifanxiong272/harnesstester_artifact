let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    describe('testpilot_subject.file_0015.processAiSdkStreamPart', function() {
        // Helper to uniformly handle sync or promise results
        async function normalizeResult(valueOrPromise) {
            return await Promise.resolve(valueOrPromise);
        }

        it('is deterministic for the same input (same output on repeated calls)', async function() {
            let samplePart = {
                type: 'message',
                id: 'part-123',
                content: {
                    role: 'assistant',
                    text: 'Hello world',
                    meta: { tokens: 3 }
                },
                timestamp: 1600000000000
            };

            let r1 = testpilot_subject.file_0015.processAiSdkStreamPart(samplePart);
            let r2 = testpilot_subject.file_0015.processAiSdkStreamPart(samplePart);

            // Await if either returned a Promise
            let v1 = await normalizeResult(r1);
            let v2 = await normalizeResult(r2);

            // The function should produce the same output for identical inputs
            assert.deepStrictEqual(v1, v2, 'Outputs differ between repeated calls with same input');
        });

            })
})