import { it, expect, vi } from 'vitest';
import { ReadMediaFileTool } from '../../../src/tools/builtin/file/read-media';
import { createFakeKaos, PERMISSIVE_WORKSPACE } from '../../tools/fixtures/fake-kaos';

it('system summary reports the actual readBytes length and not a larger stat.stSize when stat is stale', async () => {
  // Minimal PNG magic bytes so the tool recognises the data as an image.
  const PNG_HEADER = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const actualData = Buffer.concat([PNG_HEADER, Buffer.from('short')]);
  const actualLength = Buffer.byteLength(actualData);
  const staleStatSize = actualLength + 10; // intentionally larger than the actual buffer

  // Use repository fixture to get a kaos shape that includes pathClass() and gethome().
  const fakeKaos = createFakeKaos();
  // Override only the methods this probe needs.
  fakeKaos.stat = vi.fn().mockResolvedValue({ stSize: staleStatSize });
  fakeKaos.readBytes = vi.fn().mockResolvedValue(actualData);

  const capability = { image_in: true, video_in: false } as any;
  const tool = new ReadMediaFileTool(fakeKaos as any, PERMISSIVE_WORKSPACE as any, capability);

  const execution = tool.resolveExecution({ path: '/workspace/sample.png' } as any);
  const result = await execution.execute();

  const parts = (result && result.parts) || result;
  const systemText = parts && parts[0] && (parts[0] as any).text;

  const re = new RegExp(`^(?=[\\s\\S]*${actualLength} bytes)(?![\\s\\S]*${staleStatSize})[\\s\\S]*$`);
  expect(systemText).toMatch(re);
});
