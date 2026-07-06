# Launch checklist — Agent Tools API

## Before posting
- [ ] Deploy to Railway / Fly.io / Render (Dockerfile included)
- [ ] Set custom domain
- [ ] Optional: `REQUIRE_API_KEY=true` + Stripe for paid tier

## Where to post (copy-paste order)

1. **Product Hunt** — "OpenAPI → MCP tools in one API call"
2. **Show HN** — title: `Show HN: API that converts OpenAPI specs to MCP tool manifests`
3. **RapidAPI** — list with free tier (50 conversions/mo)
4. **Postman API Network** — publish collection pointing to your docs
5. **r/LangChain, r/LocalLLaMA, r/webdev** — tutorial post, not spam
6. **Dev.to** — "How to expose your REST API to Claude as MCP tools"

## Suggested pricing (when you add Stripe)

| Tier | Price | Limit |
|------|-------|-------|
| Free | $0 | 50 conversions/mo |
| Indie | $19/mo | 2,000/mo |
| Team | $49/mo | 10,000/mo |

## Show HN body template

> I built a small API that takes an OpenAPI 3 spec (JSON, YAML, or URL) and returns MCP-compatible tool definitions with inputSchema, plus an agent-readiness score.
>
> Endpoints: /v1/analyze, /v1/to-mcp, /v1/to-tools, /v1/dry-run
>
> Try: `curl -X POST https://YOUR_DOMAIN/v1/to-mcp -H 'Content-Type: application/json' -d '{"spec_url":"https://petstore3.swagger.io/api/v3/openapi.json"}'`
>
> Open source / feedback welcome.
