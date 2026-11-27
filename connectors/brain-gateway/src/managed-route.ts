/** A second client registration can use the same protected resource without replacing project links. */
export function managedMcpRequest(request: Request): Request {
  const url = new URL(request.url);
  if (url.pathname !== "/mcp/managed") return request;
  url.pathname = "/mcp";
  return new Request(url, request);
}
