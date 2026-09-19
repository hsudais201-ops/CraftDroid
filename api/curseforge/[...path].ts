import type { VercelRequest, VercelResponse } from "@vercel/node";

const ALLOWED_PREFIX = "/v1/";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const apiKey = process.env.CURSEFORGE_API_KEY;
  if (!apiKey) {
    res.status(503).json({ error: "CurseForge proxy is not configured." });
    return;
  }

  const rawPath = Array.isArray(req.query.path)
    ? "/" + req.query.path.join("/")
    : typeof req.query.path === "string"
      ? "/" + req.query.path
      : "";

  if (!rawPath.startsWith(ALLOWED_PREFIX)) {
    res.status(404).json({ error: "Unknown CurseForge route." });
    return;
  }

  const upstream = new URL("https://api.curseforge.com" + rawPath);
  for (const [key, value] of Object.entries(req.query)) {
    if (key === "path") continue;
    if (Array.isArray(value)) {
      value.forEach((item) => upstream.searchParams.append(key, item));
    } else if (value != null) {
      upstream.searchParams.set(key, value);
    }
  }

  const method = req.method || "GET";
  const body = method === "GET" || method === "HEAD"
    ? undefined
    : typeof req.body === "string"
      ? req.body
      : JSON.stringify(req.body ?? {});

  try {
    const response = await fetch(upstream, {
      method,
      headers: {
        Accept: "application/json",
        "x-api-key": apiKey,
      },
      body,
    });

    const text = await response.text();
    const contentType = response.headers.get("content-type") || "application/json";

    res.setHeader("Content-Type", contentType);
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    if (method === "GET") {
      res.setHeader("Cache-Control", "public, max-age=60, s-maxage=60");
    }
    res.status(response.status).send(text);
  } catch (error) {
    res.status(502).json({
      error: error instanceof Error ? error.message : "CurseForge upstream request failed.",
    });
  }
}

export const config = {
  api: {
    bodyParser: false,
  },
};
