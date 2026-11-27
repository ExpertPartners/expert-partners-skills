import { departmentForToken, DEPARTMENTS, type Principal } from "./access.ts";
import { isAllowedEmail } from "./allow.ts";

type Bindings = { DEPARTMENT_TOKEN_HASHES?: string; MCP_RESOURCE: string };

/** Only the provider calls this after its own bearer validation has not found a grant. */
export async function resolveDepartmentToken({ token, env }: { token: string; env: Bindings }) {
	const department = await departmentForToken(env.DEPARTMENT_TOKEN_HASHES, token);
	return department ? { props: { kind: "department", department }, audience: env.MCP_RESOURCE } : null;
}

/** Props must come from the provider's verified context, never request headers or tool arguments. */
export function mcpPrincipal(props: unknown, allowedEmails: string | undefined): Principal | null {
	if (!props || typeof props !== "object") return null;
	const p = props as Record<string, unknown>;
	if (p.kind === "department") {
		return typeof p.department === "string" && Object.prototype.hasOwnProperty.call(DEPARTMENTS, p.department)
			? { kind: "department", id: p.department } : null;
	}
	// Existing OAuth grants have no kind discriminator.
	return typeof p.email === "string" && isAllowedEmail(allowedEmails, p.email)
		? { kind: "person", email: p.email } : null;
}
