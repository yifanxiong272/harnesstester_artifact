let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Grab the function under test once
    const fn = testpilot_subject
        && testpilot_subject.file_0003
        && testpilot_subject.file_0003.ToolCallComponent
        && testpilot_subject.file_0003.ToolCallComponent.prototype
        && testpilot_subject.file_0003.ToolCallComponent.prototype.getCombinedSubagentText;

    it('is available as a function', function(done) {
        assert.ok(typeof fn === 'function', 'getCombinedSubagentText should be a function');
        done();
    });

    // Helper: build a context object that exposes many common property names
    // (so the method will find one of them regardless of the exact implementation).
    function makeContextWithArray(arr) {
        // Create an element wrapper that is tolerant: provides many common fields and toString
        function makeElem(text) {
            const obj = {
                name: text,
                text: text,
                label: text,
                displayName: text,
                toString: function() { return text; }
            };
            return obj;
        }

        const elems = arr.map(makeElem);

        // Provide many possible property names the implementation might use
        const ctx = {
            subagents: elems,
            SubAgents: elems,
            subAgentList: elems,
            subAgentArray: elems,
            sub_agent: elems,
            subs: elems,
            subList: elems,
            agents: elems,
            items: elems,
            // also provide a getter method if implementation calls one
            getSubagents: function() { return elems; }
        };

        return ctx;
    }

    })