let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // helper to handle sync or Promise results
    function handleResult(res, sessionId, done, extraChecks) {
        if (res && typeof res.then === 'function') {
            res.then(r => {
                try {
                    const s = JSON.stringify(r);
                    assert.ok(s.includes(sessionId), 'result should include the sessionId value');
                    if (extraChecks) extraChecks(r);
                    done();
                } catch (e) {
                    done(e);
                }
            }).catch(done);
        } else {
            try {
                const s = JSON.stringify(res);
                assert.ok(s.includes(sessionId), 'result should include the sessionId value');
                if (extraChecks) extraChecks(res);
                done();
            } catch (e) {
                done(e);
            }
        }
    }

    it('KimiCore and getSessionMetadata exist', function() {
        assert.ok(testpilot_subject, 'testpilot_subject should be present');
        assert.ok(testpilot_subject.file_0002, 'file_0002 should be present on testpilot_subject');
        const KimiCore = testpilot_subject.file_0002.KimiCore;
        assert.ok(KimiCore, 'KimiCore should be exported');
        assert.equal(typeof KimiCore.prototype.getSessionMetadata, 'function', 'getSessionMetadata should be a function on the prototype');
    });

    })