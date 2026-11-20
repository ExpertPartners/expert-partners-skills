/** Sign-in is limited to Allison's accounts, listed comma separated in the ALLOWED_EMAILS var. */
export function isAllowedEmail(list: string | undefined, email: string | undefined | null): boolean {
	if (!list || !email) return false;
	const allowed = list
		.split(",")
		.map((e) => e.trim().toLowerCase())
		.filter(Boolean);
	return allowed.includes(email.trim().toLowerCase());
}
