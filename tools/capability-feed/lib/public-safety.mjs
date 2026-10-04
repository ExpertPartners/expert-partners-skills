// Public-safety gate for the AI Workforce feed.
//
// Two layers, both fail closed:
//   1. Projection. build-feed.mjs constructs every record field by field from an
//      explicit list of source fields. Nothing is copied wholesale, so a private
//      frontmatter key, an access list, or an internal note on a source can never
//      ride into the feed just because it exists. (Tested in test/feed.test.mjs.)
//   2. Scan. scanForLeaks() walks every string in the finished envelope and
//      refuses the whole feed if any value looks like a credential, a secret
//      reference, a private repository URL, contact details, or a private host.
//      A refused feed is never written, so the last good feed stays in place.

export const LEAK_RULES = [
  { id: '1password-reference', rx: /\bop:\/\/\S+/i },
  { id: 'private-key-block', rx: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { id: 'aws-access-key', rx: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/ },
  { id: 'github-token', rx: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}/ },
  { id: 'api-key-prefix', rx: /\b(?:sk|pk|rk)-(?:live|test|ant|proj)?[-_]?[A-Za-z0-9]{20,}\b|\bfc-[a-f0-9]{24,}\b|\bxox[abprs]-[A-Za-z0-9-]{10,}/ },
  { id: 'jwt', rx: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}/ },
  { id: 'credential-assignment', rx: /\b(?:client[_-]?secret|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd)\s*[:=]\s*\S+/i },
  { id: 'bearer-token', rx: /\bBearer\s+[A-Za-z0-9._~+/-]{16,}/ },
  { id: 'private-github-url', rx: /github\.com\/ExpertPartners\b|api\.github\.com\/repos\/ExpertPartners\b/i },
  { id: 'email-address', rx: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/ },
  { id: 'phone-number', rx: /(?<![\w.])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?![\w.])/ },
  { id: 'private-host', rx: /\b[\w-]+\.(?:local|internal|ts\.net)\b/i },
  { id: 'tailnet-address', rx: /\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b/ },
];

function* strings(value, at) {
  if (typeof value === 'string') { yield [at, value]; return; }
  if (Array.isArray(value)) { for (let i = 0; i < value.length; i++) yield* strings(value[i], `${at}[${i}]`); return; }
  if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      yield [`${at}{key}`, k];
      yield* strings(v, `${at}.${k}`);
    }
  }
}

/** Every leak finding in the value, as { rule, at, excerpt }. Excerpts are masked. */
export function scanForLeaks(value, root = '$') {
  const findings = [];
  for (const [at, text] of strings(value, root)) {
    for (const rule of LEAK_RULES) {
      const m = text.match(rule.rx);
      if (m) findings.push({ rule: rule.id, at, excerpt: mask(m[0]) });
    }
  }
  return findings;
}

// Never echo a full matched secret into CI logs.
function mask(s) {
  return s.length <= 8 ? '****' : `${s.slice(0, 4)}...${s.slice(-2)} (${s.length} chars)`;
}

/** A public link is https, carries no credentials, and does not point into a private repo. */
export function isPublicSafeUrl(url) {
  let u;
  try { u = new URL(url); } catch { return false; }
  if (u.protocol !== 'https:') return false;
  if (u.username || u.password) return false;
  return scanForLeaks(url).length === 0;
}
