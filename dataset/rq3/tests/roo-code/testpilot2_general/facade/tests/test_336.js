let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    const parse = testpilot_subject.file_0007.parseApiReqStartedText;

    it('returns parsed object when say is "api_req_started" and text is valid JSON', function() {
        const message = {
            say: "api_req_started",
            text: JSON.stringify({ ok: true, count: 5, name: "demo" })
        };
        const result = parse(message);
        assert.deepStrictEqual(result, { ok: true, count: 5, name: "demo" });
    });

    })