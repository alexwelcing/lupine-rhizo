/** Match the same nonempty path segments as the Agents SDK. */
export function isWorkspaceRoute(pathname: string): boolean {
  const parts = pathname.split("/").filter(Boolean);
  return parts[0] === "workspace" ||
    (parts[0] === "agents" && parts[1] === "research-workspace");
}

/** Run before forwarding to the DO, including HTTP history and WebSockets. */
export function checkWorkspaceRequest(request: Request): Response | null {
  const url = new URL(request.url);
  if (!isWorkspaceRoute(url.pathname)) return null;
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts[0] === "agents" && !/^[a-z0-9][a-z0-9-]{0,63}$/.test(parts[2] ?? "")) {
    return Response.json({ error: "Invalid conversation ID" }, { status: 400 });
  }
  // Access cookies can accompany cross-origin WebSocket handshakes. Reject
  // those before the upgrade; authenticated non-browser callers omit Origin.
  const origin = request.headers.get("Origin");
  if (origin && origin !== url.origin) {
    return Response.json({ error: "Workspace requests must use the same origin" }, { status: 403 });
  }
  return null;
}

export const WORKSPACE_PRIVATE_HEADERS = {
  "Cache-Control": "private, no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "same-origin",
} as const;
