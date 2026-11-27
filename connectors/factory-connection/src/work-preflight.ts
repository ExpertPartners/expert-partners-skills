// Policy is a derived view of existing owning records, never another work queue.
export type WorkIntent = {
 action: "source_search" | "replacement_build" | "continue" | "inspect" | "escalate";
 capabilityId: string;
 evidence?: string[];
 recommendation?: string;
};
export type WorkPolicy = {
 version: 1;
 source: { url: string; revision: string };
 items: {
  id: string; aliases: string[]; sourceRecovery: "closed" | "open";
  decisionUrl: string; ownerSession: string; implementation: string;
  installed: boolean; replacementApproved: boolean;
  evidence: string[];
 }[];
};
export function validPolicy(p: unknown): p is WorkPolicy {
 const v = p as WorkPolicy;
 return !!v && v.version === 1 && !!v.source?.url && !!v.source.revision &&
  Array.isArray(v.items) && v.items.every(i => !!i.id && Array.isArray(i.aliases) &&
   i.aliases.every(a => typeof a === "string" && a.length > 2) &&
   ["closed", "open"].includes(i.sourceRecovery) && !!i.decisionUrl &&
   typeof i.ownerSession === "string" && typeof i.implementation === "string" &&
   typeof i.installed === "boolean" && typeof i.replacementApproved === "boolean" &&
   Array.isArray(i.evidence));
}
export function workPreflight(policy: WorkPolicy, intent: WorkIntent, targetSession?: string) {
 const item = policy.items.find(i => i.id === intent.capabilityId);
 const evidence = item ? [item.decisionUrl, ...item.evidence] : intent.evidence ?? [];
 const result = (allowed: boolean, code: string, reason: string) => ({
  allowed, code, reason, capabilityId: intent.capabilityId,
  ownerSession: item?.ownerSession || null, evidence, source: policy.source,
 });
 if (intent.action === "inspect") return result(true, "INSPECTION", "Read existing records without commissioning work.");
 if (intent.action === "escalate") return result(!!intent.recommendation?.trim() && !!intent.evidence?.length,
  "FOUNDER_RECOMMENDATION", "Carry the specific recommendation and source evidence to Allison through the existing owner.");
 if (!item) return result(false, "RECONCILE_FIRST", "Reconcile current decisions, gap dispositions, installed capability and ownership in the existing records first.");
 if (intent.action === "source_search") return result(false,
  item.sourceRecovery === "closed" ? "SOURCE_RECOVERY_CLOSED" : "EXISTING_SEARCH_OWNER",
  item.sourceRecovery === "closed" ? "Allison closed source recovery. Only an explicit superseding decision in the owning record can reopen it." :
   "Use the existing source owner and its one bounded search assignment. This preflight does not commission another search.");
 if (intent.action === "replacement_build") return result(false,
  item.installed ? "CAPABILITY_EXISTS" : item.ownerSession ? "EXISTING_BUILD_OWNER" : "RECONCILE_FIRST",
  item.installed ? "Reuse or extend the installed capability through its existing owner." :
   "A replacement is not a new commission. Route it to the existing owner; unassigned work needs reconciliation first.");
 if (intent.action === "continue") return result(!!item.replacementApproved && !!item.ownerSession && targetSession === item.ownerSession,
  "EXISTING_OWNER_CONTINUATION", "Approved implementation continues only in its existing owner session. Source closure does not close implementation or imply a test pass.");
 return result(false, "INVALID_ACTION", "Unknown action.");
}

/** A backstop for legacy free-text dispatches. Explicit metadata is the complete contract;
 * arbitrary natural-language/tool routes cannot be proven equivalent to that contract. */
export function legacyIntent(policy: WorkPolicy, text: string): WorkIntent | null {
 const lower = text.toLowerCase();
 const search = /\b(search|hunt|recover|find|locate)\b[^.!?\n]{0,140}\b(original|video|homework|replay|source|capstone|build 101)\b/i;
 const build = /\b(build|commission|rebuild|create|implement)\b/i;
 for (const sentence of lower.split(/[.!?\n]+/)) {
  if (/\b(no|not|never|don't|do not|closed|rejected|without|stop)\b/.test(sentence)) continue;
  const item = policy.items.find(i => [i.id, ...i.aliases].some(a => sentence.includes(a.toLowerCase())));
  if (!item) continue;
  if (search.test(sentence)) return { action: "source_search", capabilityId: item.id };
  if (build.test(sentence)) return { action: "replacement_build", capabilityId: item.id };
 }
 return null;
}
