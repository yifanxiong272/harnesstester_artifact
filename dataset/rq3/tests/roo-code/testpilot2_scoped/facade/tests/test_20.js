let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper that tries a few common ways a "summary" sentinel might be represented
    function findLastSummaryIndex(messages) {
        if (!Array.isArray(messages)) return -1;
        let last = -1;
        for (let i = 0; i < messages.length; i++) {
            let m = messages[i];
            if (!m) continue;
            // check various common summary sentinel shapes / fields
            try {
                if (m === 'SUMMARY' || m === 'Summary') { last = i; continue; }
                if (typeof m === 'string' && /summary/i.test(m)) { last = i; continue; }
                if (typeof m === 'object') {
                    if (m.summary === true) { last = i; continue; }
                    if (typeof m.type === 'string' && /summary/i.test(m.type)) { last = i; continue; }
                    if (typeof m.role === 'string' && /summary/i.test(m.role)) { last = i; continue; }
                    if (typeof m.content === 'string' && /summary/i.test(m.content)) { last = i; continue; }
                    if (typeof m.text === 'string' && /summary/i.test(m.text)) { last = i; continue; }
                    if (typeof m.body === 'string' && /summary/i.test(m.body)) { last = i; continue; }
                }
            } catch (e) {
                // ignore and continue
            }
        }
        return last;
    }

    it('returns an array and does not mutate the input', function() {
        let messages = [
            {id: 1, text: 'first'},
            {id: 2, text: 'second'},
            {id: 3, text: 'third'}
        ];
        // copy for mutation check
        let copy = JSON.parse(JSON.stringify(messages));
        let result = testpilot_subject.file_0004.getMessagesSinceLastSummary(messages);
        assert.ok(Array.isArray(result), 'result should be an array');
        // should not mutate original input
        assert.deepStrictEqual(messages, copy, 'original messages should not be mutated');
        // returned elements, if any, must be references to items from original (or deep-equal)
        result.forEach(r => {
            // either the same object reference or deep-equal to one of original entries
            let foundByRef = messages.indexOf(r) !== -1;
            let foundByDeep = messages.some(m => {
                try { return JSON.stringify(m) === JSON.stringify(r); } catch (e) { return false; }
            });
            assert.ok(foundByRef || foundByDeep, 'each returned element should correspond to an original message');
        });
    });

    })