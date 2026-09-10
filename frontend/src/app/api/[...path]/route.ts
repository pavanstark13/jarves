/**
 * Server-side proxy from the console to the agent's API.
 *
 * This exists instead of a next.config rewrite for two reasons:
 *
 *  1. A rewrite cannot attach a secret. The API token is read here, on the
 *     server, and never reaches the browser.
 *  2. A rewrite fails opaquely. Pointing a hosted console at a backend on your
 *     own machine returns Vercel's `DNS_HOSTNAME_RESOLVED_PRIVATE` 404 with no
 *     explanation; this returns a message that says what to change.
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';
const API_TOKEN = process.env.API_TOKEN ?? '';

/** Hosts that only resolve on the machine the backend runs on. */
function isPrivateHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  if (host === 'localhost' || host.endsWith('.local') || host === '::1') return true;
  if (/^127\./.test(host) || /^10\./.test(host) || /^192\.168\./.test(host)) return true;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(host)) return true;
  return false;
}

function configurationError(): NextResponse | null {
  let backend: URL;
  try {
    backend = new URL(BACKEND_URL);
  } catch {
    return NextResponse.json(
      { detail: `BACKEND_URL is not a valid URL: "${BACKEND_URL}"` },
      { status: 500 },
    );
  }

  // Deployed (Vercel sets this) but pointed at a machine-local address.
  if (process.env.VERCEL && isPrivateHost(backend.hostname)) {
    return NextResponse.json(
      {
        detail:
          `This console is deployed, but BACKEND_URL points at ${backend.origin}, ` +
          `which only exists on your own machine — the deployment cannot reach it. ` +
          `Either run the console locally next to the backend (npm run dev), or give ` +
          `the backend a public HTTPS address, set BACKEND_URL and API_TOKEN in the ` +
          `project's environment variables, and redeploy. See the README.`,
      },
      { status: 502 },
    );
  }
  return null;
}

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const misconfigured = configurationError();
  if (misconfigured) return misconfigured;

  const target = `${BACKEND_URL.replace(/\/$/, '')}/${path.join('/')}${request.nextUrl.search}`;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_TOKEN) headers.Authorization = `Bearer ${API_TOKEN}`;

  let body: string | undefined;
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    body = await request.text();
  }

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
      // The agent can take a moment on a cold cycle; fail before the platform does.
      signal: AbortSignal.timeout(25_000),
    });
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('Content-Type') ?? 'application/json' },
    });
  } catch (error) {
    const reason = error instanceof Error ? error.message : String(error);
    const hint =
      API_TOKEN || !process.env.VERCEL
        ? ''
        : ' If the backend requires a token, set API_TOKEN for this deployment too.';
    return NextResponse.json(
      { detail: `Cannot reach the agent API at ${BACKEND_URL}: ${reason}.${hint}` },
      { status: 502 },
    );
  }
}

type Context = { params: { path: string[] } };

export async function GET(request: NextRequest, { params }: Context) {
  return proxy(request, params.path);
}

export async function POST(request: NextRequest, { params }: Context) {
  return proxy(request, params.path);
}

export async function PUT(request: NextRequest, { params }: Context) {
  return proxy(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: Context) {
  return proxy(request, params.path);
}
