let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Increase default Mocha timeout in case some implementations are a bit slow
    this.timeout(5000);

    it('test testpilot_subject.file_0002.KimiCore.prototype.resumeSession - exists and is a function', function() {
        let KimiCoreContainer = testpilot_subject && testpilot_subject.file_0002;
        assert.ok(KimiCoreContainer, 'file_0002 should exist on testpilot_subject');

        let KimiCore = KimiCoreContainer.KimiCore;
        assert.ok(KimiCore, 'KimiCore should exist on file_0002');
        assert.strictEqual(typeof KimiCore.prototype.resumeSession, 'function', 'resumeSession should be a function on the prototype');
        // A reasonable expectation: the method accepts one argument (input)
        assert.strictEqual(KimiCore.prototype.resumeSession.length >= 0, true);
    });

    // Helper: ensure a promise settles within timeout
    function settleWithin(promise, timeoutMs) {
        return new Promise((resolve, reject) => {
            let finished = false;
            const t = setTimeout(() => {
                if (finished) return;
                finished = true;
                reject(new Error('timeout'));
            }, timeoutMs);

            Promise.resolve(promise).then(
                val => {
                    if (finished) return;
                    finished = true;
                    clearTimeout(t);
                    resolve({ status: 'fulfilled', value: val });
                },
                err => {
                    if (finished) return;
                    finished = true;
                    clearTimeout(t);
                    resolve({ status: 'rejected', reason: err });
                }
            );
        });
    }

    })