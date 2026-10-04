// The HQ consumer contract for the AI Workforce feed, mirrored field for field.
//
// Source of truth for the CONSUMER side: Expert Partners HQ (Lovable project
// c4a62eb9-e1d0-4580-bb3d-0044ab199b0d), file src/lib/ai-workforce.types.ts,
// read at commit 5cc98118f85f9ee672d1ccc3ec13bd189324c8e0 on 2026-10-03. HQ
// pins zod ^4.6.5; this package uses zod ^4 so the rules below behave the same.
//
// The producer validates every envelope it writes against this schema, so a
// feed that HQ would reject never lands. If HQ changes its schema, update this
// mirror in the same change that adapts the producer, never one without the other.

import { z } from 'zod';

export const WORKFORCE_FEED_SCHEMA = 'expert-partners-ai-workforce/v1';

export const WORKFORCE_KINDS = ['capability', 'plugin', 'skill', 'collection', 'agent'];
export const WORKFORCE_STATUSES = ['Designed', 'Active', 'Pilot', 'Migrating', 'Needs Review', 'Deprecated', 'Retired', 'Unknown'];

const str = z.string().max(2000);
const list = z.array(str).max(200);

export const workforceRecordSchema = z.object({
  id: z.string().min(1).max(120).regex(/^[a-z0-9-]+$/),
  humanName: z.string().min(1).max(200),
  kind: z.enum(WORKFORCE_KINDS),
  summary: str,
  status: z.enum(WORKFORCE_STATUSES),
  source: str.optional(),
  maintainer: str.optional(),
  verifiedOwner: str.optional(),
  collectionIds: list,
  categories: list,
  portable: z.union([z.boolean(), z.literal('unknown')]),
  verifiedSurfaces: list,
  invocationInstructions: list,
  sourceLinks: z.array(z.object({ label: z.string().max(200), url: z.string().url().startsWith('https://') })).max(20),
  lastVerified: str,
  containsSkillIds: list,
  replacedBy: str.optional(),
  replaces: str.optional(),
  relatedIds: list,
  accessNote: str,
  technicalDetail: z.record(z.string(), str),
  need: z.string().optional(),
  keywords: list,
  bestFor: list,
  useCases: list,
  askExamples: list,
  outcome: str.optional(),
  example: z.boolean(),
});

export const workforceEnvelopeSchema = z.object({
  schema: z.literal(WORKFORCE_FEED_SCHEMA),
  source: z.enum(['local-fallback', 'canonical']),
  generatedAt: z.string().datetime(),
  verifiedAt: z.string().datetime().nullable(),
  records: z.array(workforceRecordSchema).max(5000),
});

/** Same behavior as HQ's parseWorkforceEnvelope: the parsed envelope, or null. */
export function parseWorkforceEnvelope(input) {
  const result = workforceEnvelopeSchema.safeParse(input);
  return result.success ? result.data : null;
}

/** The issues HQ's schema would raise for this envelope (empty when it passes). */
export function contractIssues(input) {
  const result = workforceEnvelopeSchema.safeParse(input);
  return result.success ? [] : result.error.issues.map(i => `${i.path.join('.') || '(root)'}: ${i.message}`);
}
