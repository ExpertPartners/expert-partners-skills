import { BRAIN_FOLDERS, type DriveFetch } from "../src/brain.ts";

const roots: ReadonlySet<string> = new Set(Object.values(BRAIN_FOLDERS));

/** Supply only registered-root preflights; all other requests still exercise the fixture's Drive. */
export function withRoots(drive: DriveFetch, opts: { driveId?: string; calls?: string[] } = {}): DriveFetch {
	return async (path) => {
		const url = new URL(path, "https://drive.invalid");
		const match = url.pathname.match(/^\/drive\/v3\/files\/([^/]+)$/);
		const id = match ? decodeURIComponent(match[1]!) : undefined;
		if (id && roots.has(id) && url.searchParams.get("fields") === "id,mimeType,trashed,driveId") {
			opts.calls?.push(path);
			return Response.json({ id, mimeType: "application/vnd.google-apps.folder", trashed: false, driveId: opts.driveId ?? "D1" });
		}
		return drive(path);
	};
}
