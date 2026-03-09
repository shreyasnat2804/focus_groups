"""Tests for frontend Docker configuration files."""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


class TestDockerfile:
    """Validate frontend/Dockerfile exists and contains expected stages."""

    def test_exists(self):
        assert (FRONTEND / "Dockerfile").is_file()

    def test_build_stage(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "FROM node:20-alpine AS builder" in content

    def test_runtime_stage(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "FROM nginx:1.27-alpine" in content

    def test_vite_api_url_arg(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "ARG VITE_API_URL" in content
        assert "ENV VITE_API_URL" in content

    def test_npm_ci(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "npm ci" in content

    def test_npm_run_build(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "npm run build" in content

    def test_expose_8080(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "EXPOSE 8080" in content

    def test_copies_nginx_conf(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "nginx.conf" in content

    def test_copies_dist(self):
        content = (FRONTEND / "Dockerfile").read_text()
        assert "COPY --from=builder /app/dist" in content


class TestNginxConf:
    """Validate frontend/nginx.conf exists and contains key directives."""

    def test_exists(self):
        assert (FRONTEND / "nginx.conf").is_file()

    def test_listen_8080(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "listen 8080" in content

    def test_try_files_spa_fallback(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "try_files" in content
        assert "/index.html" in content

    def test_api_proxy(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "location /api/" in content
        assert "proxy_pass http://api:8080" in content

    def test_health_endpoint(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "location /health" in content
        assert "return 200" in content

    def test_security_headers(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content

    def test_static_asset_caching(self):
        content = (FRONTEND / "nginx.conf").read_text()
        assert "expires" in content
        assert "Cache-Control" in content

    def test_security_headers_in_static_location(self):
        """Static asset location block must repeat security headers.

        Nginx does NOT inherit server-level add_header into location blocks
        that define their own add_header directives.
        """
        content = (FRONTEND / "nginx.conf").read_text()
        # Find the static assets location block
        in_static_block = False
        brace_depth = 0
        static_block_lines = []
        for line in content.splitlines():
            if "location ~*" in line and "(js|css|" in line:
                in_static_block = True
            if in_static_block:
                brace_depth += line.count("{") - line.count("}")
                static_block_lines.append(line)
                if brace_depth == 0 and static_block_lines:
                    break
        static_block = "\n".join(static_block_lines)
        assert "X-Content-Type-Options" in static_block, (
            "Static asset location must include X-Content-Type-Options "
            "(nginx does not inherit server-level add_header)"
        )
        assert "X-Frame-Options" in static_block, (
            "Static asset location must include X-Frame-Options"
        )


class TestDockerignore:
    """Validate frontend/.dockerignore exists and excludes expected paths."""

    def test_exists(self):
        assert (FRONTEND / ".dockerignore").is_file()

    def test_excludes_node_modules(self):
        content = (FRONTEND / ".dockerignore").read_text()
        assert "node_modules" in content

    def test_excludes_dist(self):
        content = (FRONTEND / ".dockerignore").read_text()
        assert "dist" in content

    def test_excludes_env(self):
        content = (FRONTEND / ".dockerignore").read_text()
        assert ".env" in content

    def test_excludes_test_files(self):
        content = (FRONTEND / ".dockerignore").read_text()
        assert "*.test.js" in content


class TestApiModule:
    """Validate frontend/src/api.js exports apiUrl and uses VITE_API_URL."""

    def test_exists(self):
        assert (FRONTEND / "src" / "api.js").is_file()

    def test_exports_api_url(self):
        content = (FRONTEND / "src" / "api.js").read_text()
        assert "export function apiUrl" in content

    def test_uses_vite_api_url(self):
        content = (FRONTEND / "src" / "api.js").read_text()
        assert "import.meta.env.VITE_API_URL" in content

    def test_base_uses_api_url_prefix(self):
        """BASE should incorporate VITE_API_URL for production builds."""
        content = (FRONTEND / "src" / "api.js").read_text()
        assert "VITE_API_URL" in content
        lines = content.split("\n")
        base_lines = [l for l in lines if l.startswith("const BASE")]
        assert len(base_lines) > 0
        for line in base_lines:
            assert "VITE_API_URL" in line or "API_BASE" in line
