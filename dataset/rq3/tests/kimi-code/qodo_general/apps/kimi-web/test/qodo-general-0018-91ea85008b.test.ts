import { describe, expect, it } from 'vitest';
import {
  collectFilePathAliases,
  findFilePathLinks,
  parseFilePathLinkCandidate,
} from '../src/lib/filePathLinks';
import { parseDiff } from '../src/lib/parseDiff';
import { normalizeToolName, toolSummary } from '../src/lib/toolMeta';
import { i18n } from '../src/i18n';
import { toolGlyph, toolChip } from '../src/lib/toolMeta';
import { toolLabel } from '../src/lib/toolMeta';
import { toolChip } from '../src/lib/toolMeta';
import { toolSummary } from '../src/lib/toolMeta';
import { toolGlyph } from '../src/lib/toolMeta';

describe('parseDiff', () => {
  it('parses multiple files and keeps hunk line numbers', () => {
    const diff = [
      'diff --git a/src/a.ts b/src/a.ts',
      'index 1111111..2222222 100644',
      '--- a/src/a.ts',
      '+++ b/src/a.ts',
      '@@ -1,2 +1,3 @@',
      ' const a = 1;',
      '-const b = 2;',
      '+const b = 3;',
      '+const c = 4;',
      'diff --git a/src/comment.sql b/src/comment.sql',
      '@@ -5,1 +5,1 @@',
      '--- old comment',
      '+++ new comment',
    ].join('\n');

    expect(parseDiff(diff)).toEqual([
      { type: 'hunk', text: '@@ -1,2 +1,3 @@' },
      { type: 'context', text: 'const a = 1;', oldNo: 1, newNo: 1 },
      { type: 'del', text: 'const b = 2;', oldNo: 2 },
      { type: 'add', text: 'const b = 3;', newNo: 2 },
      { type: 'add', text: 'const c = 4;', newNo: 3 },
      { type: 'hunk', text: '@@ -5,1 +5,1 @@' },
      { type: 'del', text: '-- old comment', oldNo: 5 },
      { type: 'add', text: '++ new comment', newNo: 5 },
    ]);
  });
});

describe('filePathLinks', () => {
  it('rejects URLs and bare unknown filenames', () => {
    expect(parseFilePathLinkCandidate('https://example.com/a.ts')).toBeNull();
    expect(parseFilePathLinkCandidate('e2e-success.png')).toBeNull();
  });

  it('finds path links with line numbers and resolves aliases', () => {
    const aliases = collectFilePathAliases('<img src="/assets/demo.png">');
    expect(aliases.get('demo.png')).toBe('/assets/demo.png');

    expect(
      findFilePathLinks('Open src/a.ts#L12 and demo.png.', { aliases }),
    ).toMatchObject([
      { path: 'src/a.ts', line: 12, text: 'src/a.ts#L12' },
      { path: '/assets/demo.png', text: 'demo.png' },
    ]);
  });
});

describe('toolMeta', () => {
  it('normalizes common tool aliases', () => {
    expect(normalizeToolName('WebFetch')).toBe('web_fetch');
    expect(normalizeToolName('MultiEdit')).toBe('multi_edit');
    expect(normalizeToolName('TodoWrite')).toBe('todo');
    expect(normalizeToolName('rg')).toBe('grep');
  });

  it('summarizes tool arguments for card headers', () => {
    expect(
      toolSummary('Read', JSON.stringify({ path: 'src/a.ts', offset: 10, limit: 5 })),
    ).toBe('src/a.ts:10-15');
    expect(toolSummary('Read', '{}')).toBe('');
    expect(toolSummary('Bash', JSON.stringify({ command: 'pnpm test' }))).toBe('pnpm test');
    expect(
      toolSummary('WebFetch', JSON.stringify({ url: 'https://example.com/path/to' })),
    ).toBe('example.com/path');
  });
});

  it('falls back to the raw arg for unknown tools (default branch)', () => {
    const jsonArg = JSON.stringify({ a: 1, b: 2 });
    // Unknown tool kind, but arg is a JSON-object string; default branch should return
    // the (possibly clipped) arg string. Using full=false (default) but small input avoids clipping.
    expect(toolSummary('someUnknownTool', jsonArg)).toBe(jsonArg);
  });


  it('parses unified diff counts, combined summary counts, and respects error status', () => {
    // Unified diff on a single line: + before - (primary regex path)
    expect(
      toolChip({
        name: 'edit',
        arg: '',
        output: ['changed files +3 -1 lines'],
      }),
    ).toBe('+3 −1');
  
    // Minus before plus so the primary regex (which expects +...-) does not match,
    // but the summary branch will still find both + and - and combine them.
    expect(
      toolChip({
        name: 'write',
        arg: '',
        output: ['-1 then +2'],
      }),
    ).toBe('+2 −1');
  
    // No counts and status is 'error' → should return empty (do not show "edited")
    expect(
      toolChip({
        name: 'edit',
        arg: '',
        output: ['no diff counts here'],
        status: 'error',
      }),
    ).toBe('');
  });


  it('toolChip prefers timing for bash and returns empty string on exceptions', () => {
    // Bash should prefer timing if present
    expect(toolChip({ name: 'bash', arg: '', timing: '0.123s' })).toBe('0.123s');
  
    // If accessing output throws, the function should catch and return empty string
    const badTool: any = {
      name: 'edit',
      arg: '',
      get output() {
        throw new Error('boom');
      },
    };
    expect(toolChip(badTool)).toBe('');
  });


  it('toolChip produces diffs, simple summaries, edited fallback, read lines and grep empty', () => {
    // Unified diff style first-loop match
    expect(toolChip({ name: 'write', arg: '', output: ['+12 -3'] })).toBe('+12 −3');
  
    // Simple summary matching +N and -M elsewhere in the output
    expect(toolChip({ name: 'edit', arg: '', output: ['some summary +5 removed -2 lines'] })).toBe('+5 −2');
  
    // Fallback "edited" when no numeric diff info but output exists and status !== 'error'
    expect(toolChip({ name: 'multi_edit', arg: '', output: ['no numbers here'], status: 'ok' })).toBe(i18n.global.t('tools.chip.edited'));
  
    // Read with output lines should produce the localized "lines" string containing the count
    expect(toolChip({ name: 'read', arg: '', output: ['one','two'] })).toBe(i18n.global.t('tools.chip.lines', { count: 2 }));
  
    // Grep/search with no results should return empty string
    expect(toolChip({ name: 'grep', arg: '', output: [] })).toBe('');
  });


  it('toolSummary handles read (path-only), grep (pattern-only), and todo label/items', () => {
    // Read with only a path should return the path
    expect(toolSummary('Read', JSON.stringify({ path: 'src/example.ts' }))).toBe('src/example.ts');
  
    // Grep with only a pattern should return just the pattern
    expect(toolSummary('Grep', JSON.stringify({ pattern: 'foo.*' }))).toBe('foo.*');
  
    // Todo with a description should return the description text
    expect(toolSummary('Todo', JSON.stringify({ description: 'Buy milk' }))).toBe('Buy milk');
  
    // Todo with items should return a localized string that includes the count (we don't assert exact translation)
    const itemsSummary = toolSummary('Todo', JSON.stringify({ items: ['a','b','c'] }));
    expect(itemsSummary).toContain('3');
  });


  it('toolGlyph returns correct glyphs for search, task, skill, and unknown', () => {
    // search should return the magnifier glyph (contains a circle element)
    expect(toolGlyph('search')).toContain('<circle cx="6.5"');
  
    // task should return the checklist glyph (contains the checklist polyline)
    expect(toolGlyph('task')).toContain('polyline points="2,4.5 3.5,6 5.5,3"');
  
    // names containing "skill" should return the lightning glyph (unique path d)
    expect(toolGlyph('SuperSkill')).toContain('M8.5 1L3 9h4l-1.5 6');
  
    // unknown tools should return the empty/default glyph (empty string)
    expect(toolGlyph('some-unknown-tool')).toBe('');
  });


  it('returns the raw tool name when a label key is not available', () => {
    // Unknown label key -> should return the input name unchanged
    expect(toolLabel('some-unknown-tool')).toBe('some-unknown-tool');
    // Known keys map to label keys; we cannot assume translation content here,
    // but calling toolLabel for a known key should not return the raw name.
    const known = toolLabel('read');
    expect(typeof known).toBe('string');
    // If the translation system returns keys, at minimum the result should not be the literal input name.
    expect(known).not.toBe('read');
  });


  it('generates chips for tool outputs and parses diff summaries', () => {
    // bash prefers timing
    expect(toolChip({ name: 'bash', arg: '', timing: '12ms' })).toBe('12ms');
    expect(toolChip({ name: 'bash', arg: '' })).toBe('');
    // read: counts lines via output array -> result should be non-empty (translation applied)
    const readChip = toolChip({ name: 'read', arg: '', output: ['a','b'] });
    expect(typeof readChip).toBe('string');
    expect(readChip.length).toBeGreaterThan(0);
    // write/edit: unified diff style "+N -M" should be parsed into "+N −M" (note unicode minus)
    const diffChip = toolChip({ name: 'write', arg: '', output: ['... +12 -3 ...'] });
    expect(diffChip).toBe('+12 −3');
    // write/edit: fallback to "edited" chip (translation) when output present but no counts and status is not 'error'
    const editedChip = toolChip({ name: 'edit', arg: '', output: ['no counts here'], status: 'ok' });
    expect(typeof editedChip).toBe('string');
    expect(editedChip.length).toBeGreaterThan(0);
    // grep/search: returns results count when output exists (non-empty string expected)
    const grepChip = toolChip({ name: 'rg', arg: '', output: ['match1','match2'] });
    expect(typeof grepChip).toBe('string');
    expect(grepChip.length).toBeGreaterThan(0);
    // unknown/default tools produce empty chip
    expect(toolChip({ name: 'unknown', arg: '' })).toBe('');
  });


  it('produces concise summaries for many tool argument shapes', () => {
    // read with start only
    expect(toolSummary('Read', JSON.stringify({ path: 'a.txt', start_line: 3 }))).toBe('a.txt:3');
    // read with empty object: collapsed header should be empty, full mode should show the raw arg
    expect(toolSummary('Read', '{}')).toBe('');
    expect(toolSummary('Read', '{}', true)).toBe('{}');
    // write with path should prefix the created chip text (translation text is not asserted exactly,
    // but the returned string should start with the path and two spaces as per implementation)
    const writeOut = toolSummary('Write', JSON.stringify({ path: 'file.txt' }));
    expect(writeOut.startsWith('file.txt  ')).toBe(true);
    // edit should return the file path (various file path key names supported)
    expect(toolSummary('Edit', JSON.stringify({ filePath: '/x/y' }))).toBe('/x/y');
    // bash: long commands are clipped in non-full mode and preserved in full mode
    const longCmd = 'a'.repeat(200);
    const short = toolSummary('Bash', JSON.stringify({ command: longCmd }));
    expect(short.length).toBeLessThanOrEqual(64);
    expect(short.endsWith('…')).toBe(true);
    const full = toolSummary('Bash', JSON.stringify({ command: longCmd }), true);
    expect(full).toBe(longCmd);
    // grep/search: pattern + path
    expect(toolSummary('Grep', JSON.stringify({ pattern: 'foo', path: 'src' }))).toBe('foo  in src');
    // glob: pattern + path, and fallback to returning only path when only path present
    expect(toolSummary('Glob', JSON.stringify({ pattern: '*.ts', path: 'lib' }))).toBe('*.ts  in lib');
    expect(toolSummary('Glob', JSON.stringify({ path: '/the/dir' }))).toBe('/the/dir');
    // ls: various dir keys
    expect(toolSummary('ls', JSON.stringify({ cwd: '/home' }))).toBe('/home');
    // web_fetch: malformed URL should be returned without protocol (urlHost fallback path)
    expect(toolSummary('WebFetch', JSON.stringify({ url: 'not-a-url' }))).toBe('not-a-url');
    // invalid JSON starting with '{' but not parseable should fall back to the raw arg string
    const invalid = '{not json}';
    expect(toolSummary('Something', invalid)).toBe(invalid);
  });


  it('returns correct glyphs for known tools and handles defaults', () => {
    // Known glyphs contain distinctive fragments from the SVG strings.
    expect(toolGlyph('read')).toContain('<rect x="2.5" y="1.5" width="9" height="13" rx="1"/>');
    expect(toolGlyph('bash')).toContain('<polyline points="4,6 6.5,8 4,10"/>');
    expect(toolGlyph('edit')).toContain('M10.5 2.5l3 3-8 8H2.5v-3l8-8z');
    // MultiEdit is an alias for edit
    expect(toolGlyph('MultiEdit')).toContain('M10.5 2.5l3 3-8 8H2.5v-3l8-8z');
    expect(toolGlyph('write')).toContain('M3 12V4.5L8 2l5 2.5V12H3z');
    expect(toolGlyph('grep')).toContain('<circle cx="6.5" cy="6.5" r="4"/>');
    expect(toolGlyph('glob')).toContain('x1="8" y1="6" x2="8" y2="10"');
    expect(toolGlyph('ls')).toContain('M1.5 4.5a1 1 0 0 1 1-1h3l1.2 1.4H13');
    expect(toolGlyph('web_fetch')).toContain('<circle cx="8" cy="8" r="6"/>');
    expect(toolGlyph('todo')).toContain('polyline points="2,4.5 3.5,6 5.5,3"');
    // Name containing 'skill' triggers the lightning glyph
    expect(toolGlyph('mySkill')).toContain('M8.5 1L3 9h4l-1.5 6 5.5-8h-4l1.5-6z');
    // Unknown tool returns empty string
    expect(toolGlyph('totally-unknown-tool')).toBe('');
  });

