let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0003.ToolCallComponent.prototype.syncSubagentElapsedTimer', function() {
    // Helper: try to find a numeric property that looks like an "elapsed" or "timer" value
    function findElapsedLikeProperty(obj) {
        const regex = /(elapsed|timer)/i;
        for (let k of Object.keys(obj)) {
            if (regex.test(k)) {
                let v = obj[k];
                if (typeof v === 'number' && !Number.isNaN(v) && Number.isFinite(v)) {
                    return { key: k, value: v };
                }
                // sometimes it may be nested as an object { elapsed: 123 } or similarly
                if (v && typeof v === 'object') {
                    for (let nk of Object.keys(v)) {
                        if (regex.test(nk) && typeof v[nk] === 'number') {
                            return { key: k + '.' + nk, value: v[nk] };
                        }
                    }
                }
            }
        }
        return null;
    }

    it('should expose syncSubagentElapsedTimer as a function', function() {
        const proto = testpilot_subject.file_0003.ToolCallComponent && testpilot_subject.file_0003.ToolCallComponent.prototype;
        assert(proto, 'ToolCallComponent.prototype not found on module');
        assert.strictEqual(typeof proto.syncSubagentElapsedTimer, 'function', 'syncSubagentElapsedTimer should be a function');
    });

    })