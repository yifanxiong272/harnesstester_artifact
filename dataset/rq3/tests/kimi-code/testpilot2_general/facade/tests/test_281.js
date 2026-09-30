let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('test testpilot_subject', function() {
    // Prepare global stubs used by the method under test
    beforeEach(function() {
        // __name should return the formatter function (first arg) so that
        // accent(...) behaves as a simple formatting function.
        global.__name = (fn, name) => fn;

        // Simple theme stubs: fg and dim will mark strings so tests can assert them.
        global.import_theme = {
            currentTheme: {
                fg: (variant, text) => `fg(${variant}):${text}`,
                dim: (text) => `dim:${text}`
            }
        };

        // Simple Text class that stores the content so we can inspect it.
        global.import_pi_tui = {
            Text: class {
                constructor(text, x, y) {
                    this.text = text;
                    this.x = x;
                    this.y = y;
                }
            }
        };
    });

    afterEach(function() {
        // Clean up globals to avoid leaking state between tests
        delete global.__name;
        delete global.import_theme;
        delete global.import_pi_tui;
    });

    it('returns false for invalid JSON', function(done) {
        const proto = testpilot_subject.file_0003.ToolCallComponent.prototype;
        const inst = Object.create(proto);
        inst.children = [];
        inst.addChild = function(c) { this.children.push(c); };

        const result = inst.renderAskUserQuestionResult("this is not json");
        assert.strictEqual(result, false);
        assert.strictEqual(inst.children.length, 0);
        done();
    });

    })