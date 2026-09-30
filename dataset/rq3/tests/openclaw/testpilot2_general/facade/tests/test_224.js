let mocha = require('mocha');
let assert = require('assert');
let testpilot_subject = require('..');

describe('testpilot_subject.file_0009.buildApprovalPendingMessage', function() {
    const build = testpilot_subject.file_0009.buildApprovalPendingMessage;

    it('produces a basic message without warningText or nodeId', function() {
        const params = {
            approvalSlug: "abc",
            approvalId: "abcdef123456",
            host: "example.com",
            cwd: "/home/user",
            command: "echo hello",
            // warningText: undefined
            // nodeId: undefined
        };

        const msg = build(params);
        // Basic required pieces
        assert.ok(msg.includes(`Approval required (id ${params.approvalSlug}, full ${params.approvalId}).`), 'approval line present');
        assert.ok(msg.includes(`Host: ${params.host}`), 'host line present');
        assert.ok(msg.includes(`CWD: ${params.cwd}`), 'cwd line present');
        assert.ok(msg.includes("Command:"), 'command label present');
        // fence should be the plain triple backtick for a command that does not contain backticks
        assert.ok(msg.includes("```sh\n" + params.command + "\n```"), 'command is wrapped in triple-backtick fence with sh');
        // mode and reply lines
        assert.ok(msg.includes("Mode: foreground (interactive approvals available)."), 'mode line present');
        assert.ok(msg.includes(`Reply with: /approve ${params.approvalSlug} allow-once|allow-always|deny`), 'reply with line present');
        // short-code ambiguity help line
        assert.ok(msg.includes("If the short code is ambiguous, use the full id in /approve."), 'ambiguity help present');
        // warning should not be present
        assert.ok(!msg.startsWith("Warning:"), 'no warning at start');
    });

    })