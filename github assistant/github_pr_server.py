#!/usr/bin/env python3
"""
GitHub Pull Request MCP Server
Otomatik PR yönetimi için Model Context Protocol sunucusu
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl

# GitHub API yapılandırması
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    print("Hata: GITHUB_TOKEN çevre değişkeni tanımlanmamış", file=sys.stderr)
    sys.exit(1)

# Global HTTP client
http_client = httpx.AsyncClient(
    headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    },
    timeout=30.0
)

# MCP sunucusu oluştur
app = Server("github-pr-server")

# Yardımcı fonksiyonlar
async def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """GitHub repo URL'sinden owner ve repo adını çıkar"""
    repo_url = repo_url.rstrip("/")
    
    if "github.com" in repo_url:
        parts = repo_url.split("/")
        owner = parts[-2]
        repo = parts[-1].replace(".git", "")
    else:
        # owner/repo formatında olabilir
        parts = repo_url.split("/")
        owner = parts[0]
        repo = parts[1]
    
    return owner, repo

async def github_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """GitHub API'ye istek gönder"""
    url = f"{GITHUB_API_BASE}{endpoint}"
    
    try:
        response = await http_client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_data = e.response.json() if e.response.content else {}
        raise RuntimeError(f"GitHub API hatası: {e.response.status_code} - {error_data.get('message', 'Bilinmeyen hata')}")
    except Exception as e:
        raise RuntimeError(f"İstek hatası: {str(e)}")

# Tool tanımlamaları
@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Mevcut tool'ları listele"""
    return [
        types.Tool(
            name="create_pull_request",
            description="Yeni bir pull request oluştur",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si (örn: https://github.com/owner/repo)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Pull request başlığı"
                    },
                    "body": {
                        "type": "string",
                        "description": "Pull request açıklaması"
                    },
                    "head": {
                        "type": "string",
                        "description": "Değişikliklerin bulunduğu branch"
                    },
                    "base": {
                        "type": "string",
                        "description": "Hedef branch (varsayılan: main)",
                        "default": "main"
                    },
                    "draft": {
                        "type": "boolean",
                        "description": "Draft PR olarak oluştur",
                        "default": False
                    }
                },
                "required": ["repo_url", "title", "body", "head"]
            }
        ),
        types.Tool(
            name="list_pull_requests",
            description="Repository'deki pull request'leri listele",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "state": {
                        "type": "string",
                        "description": "PR durumu: open, closed, all",
                        "default": "open",
                        "enum": ["open", "closed", "all"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maksimum sonuç sayısı",
                        "default": 10
                    }
                },
                "required": ["repo_url"]
            }
        ),
        types.Tool(
            name="get_pull_request",
            description="Belirli bir pull request'in detaylarını getir",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    }
                },
                "required": ["repo_url", "pr_number"]
            }
        ),
        types.Tool(
            name="add_pr_comment",
            description="Pull request'e yorum ekle",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Eklenecek yorum"
                    }
                },
                "required": ["repo_url", "pr_number", "comment"]
            }
        ),
        types.Tool(
            name="add_pr_review",
            description="Pull request'e review ekle",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    },
                    "body": {
                        "type": "string",
                        "description": "Review yorumu"
                    },
                    "event": {
                        "type": "string",
                        "description": "Review türü: APPROVE, REQUEST_CHANGES, COMMENT",
                        "enum": ["APPROVE", "REQUEST_CHANGES", "COMMENT"],
                        "default": "COMMENT"
                    }
                },
                "required": ["repo_url", "pr_number", "body"]
            }
        ),
        types.Tool(
            name="merge_pull_request",
            description="Pull request'i merge et",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    },
                    "merge_method": {
                        "type": "string",
                        "description": "Merge yöntemi: merge, squash, rebase",
                        "enum": ["merge", "squash", "rebase"],
                        "default": "merge"
                    },
                    "commit_title": {
                        "type": "string",
                        "description": "Merge commit başlığı (opsiyonel)"
                    }
                },
                "required": ["repo_url", "pr_number"]
            }
        ),
        types.Tool(
            name="close_pull_request",
            description="Pull request'i kapat",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    }
                },
                "required": ["repo_url", "pr_number"]
            }
        ),
        types.Tool(
            name="update_pull_request",
            description="Pull request bilgilerini güncelle",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    },
                    "title": {
                        "type": "string",
                        "description": "Yeni başlık (opsiyonel)"
                    },
                    "body": {
                        "type": "string",
                        "description": "Yeni açıklama (opsiyonel)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Durum: open veya closed",
                        "enum": ["open", "closed"]
                    }
                },
                "required": ["repo_url", "pr_number"]
            }
        ),
        types.Tool(
            name="add_pr_reviewers",
            description="Pull request'e reviewer ekle",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    },
                    "reviewers": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Eklenecek reviewer kullanıcı adları"
                    },
                    "team_reviewers": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Eklenecek takım adları (opsiyonel)"
                    }
                },
                "required": ["repo_url", "pr_number", "reviewers"]
            }
        ),
        types.Tool(
            name="get_pr_files",
            description="Pull request'teki değişen dosyaları listele",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repository URL'si"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Pull request numarası"
                    }
                },
                "required": ["repo_url", "pr_number"]
            }
        )
    ]

# Tool handler'ları
@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Tool çağrılarını işle"""
    
    if not arguments:
        raise ValueError("Argüman gerekli")
    
    try:
        if name == "create_pull_request":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            
            data = {
                "title": arguments["title"],
                "body": arguments["body"],
                "head": arguments["head"],
                "base": arguments.get("base", "main"),
                "draft": arguments.get("draft", False)
            }
            
            result = await github_request(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                json=data
            )
            
            return [types.TextContent(
                type="text",
                text=f"✅ Pull Request #{result['number']} oluşturuldu!\n\n"
                     f"**Başlık:** {result['title']}\n"
                     f"**URL:** {result['html_url']}\n"
                     f"**Durum:** {result['state']}\n"
                     f"**Draft:** {'Evet' if result['draft'] else 'Hayır'}"
            )]
        
        elif name == "list_pull_requests":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            state = arguments.get("state", "open")
            limit = arguments.get("limit", 10)
            
            params = {
                "state": state,
                "per_page": limit,
                "sort": "created",
                "direction": "desc"
            }
            
            result = await github_request(
                "GET",
                f"/repos/{owner}/{repo}/pulls",
                params=params
            )
            
            if not result:
                return [types.TextContent(
                    type="text",
                    text=f"Repository'de {state} durumunda pull request bulunamadı."
                )]
            
            pr_list = []
            for pr in result:
                pr_list.append(
                    f"#{pr['number']} - {pr['title']}\n"
                    f"   Durum: {pr['state']} | Oluşturan: {pr['user']['login']}\n"
                    f"   URL: {pr['html_url']}"
                )
            
            return [types.TextContent(
                type="text",
                text=f"📋 {owner}/{repo} repository'sindeki {state} pull request'ler:\n\n" + 
                     "\n\n".join(pr_list)
            )]
        
        elif name == "get_pull_request":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            result = await github_request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pr_number}"
            )
            
            # Review'ları da al
            reviews = await github_request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
            )
            
            review_summary = []
            for review in reviews:
                review_summary.append(f"- {review['user']['login']}: {review['state']}")
            
            return [types.TextContent(
                type="text",
                text=f"🔍 Pull Request #{pr_number} Detayları:\n\n"
                     f"**Başlık:** {result['title']}\n"
                     f"**Açıklama:** {result['body'] or 'Açıklama yok'}\n"
                     f"**Durum:** {result['state']}\n"
                     f"**Oluşturan:** {result['user']['login']}\n"
                     f"**Branch:** {result['head']['ref']} → {result['base']['ref']}\n"
                     f"**Oluşturulma:** {result['created_at']}\n"
                     f"**Değişiklik:** +{result['additions']} / -{result['deletions']}\n"
                     f"**Review'lar:**\n" + ("\n".join(review_summary) if review_summary else "Henüz review yok") + "\n"
                     f"**URL:** {result['html_url']}"
            )]
        
        elif name == "add_pr_comment":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {
                "body": arguments["comment"]
            }
            
            result = await github_request(
                "POST",
                f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
                json=data
            )
            
            return [types.TextContent(
                type="text",
                text=f"💬 Yorum eklendi!\n\n"
                     f"**PR #:** {pr_number}\n"
                     f"**Yorum:** {result['body']}\n"
                     f"**URL:** {result['html_url']}"
            )]
        
        elif name == "add_pr_review":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {
                "body": arguments["body"],
                "event": arguments.get("event", "COMMENT")
            }
            
            result = await github_request(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                json=data
            )
            
            event_map = {
                "APPROVE": "✅ Onaylandı",
                "REQUEST_CHANGES": "❌ Değişiklik İstendi",
                "COMMENT": "💭 Yorum"
            }
            
            return [types.TextContent(
                type="text",
                text=f"📝 Review eklendi!\n\n"
                     f"**PR #:** {pr_number}\n"
                     f"**Durum:** {event_map.get(data['event'], data['event'])}\n"
                     f"**Yorum:** {result['body']}\n"
                     f"**URL:** {result['html_url']}"
            )]
        
        elif name == "merge_pull_request":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {
                "merge_method": arguments.get("merge_method", "merge")
            }
            
            if "commit_title" in arguments:
                data["commit_title"] = arguments["commit_title"]
            
            result = await github_request(
                "PUT",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                json=data
            )
            
            return [types.TextContent(
                type="text",
                text=f"🎉 Pull Request #{pr_number} başarıyla merge edildi!\n\n"
                     f"**SHA:** {result['sha']}\n"
                     f"**Mesaj:** {result['message']}"
            )]
        
        elif name == "close_pull_request":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {
                "state": "closed"
            }
            
            result = await github_request(
                "PATCH",
                f"/repos/{owner}/{repo}/pulls/{pr_number}",
                json=data
            )
            
            return [types.TextContent(
                type="text",
                text=f"🔒 Pull Request #{pr_number} kapatıldı.\n\n"
                     f"**Başlık:** {result['title']}\n"
                     f"**URL:** {result['html_url']}"
            )]
        
        elif name == "update_pull_request":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {}
            if "title" in arguments:
                data["title"] = arguments["title"]
            if "body" in arguments:
                data["body"] = arguments["body"]
            if "state" in arguments:
                data["state"] = arguments["state"]
            
            result = await github_request(
                "PATCH",
                f"/repos/{owner}/{repo}/pulls/{pr_number}",
                json=data
            )
            
            return [types.TextContent(
                type="text",
                text=f"✏️ Pull Request #{pr_number} güncellendi!\n\n"
                     f"**Başlık:** {result['title']}\n"
                     f"**Durum:** {result['state']}\n"
                     f"**URL:** {result['html_url']}"
            )]
        
        elif name == "add_pr_reviewers":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            data = {
                "reviewers": arguments["reviewers"]
            }
            
            if "team_reviewers" in arguments:
                data["team_reviewers"] = arguments["team_reviewers"]
            
            result = await github_request(
                "POST",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers",
                json=data
            )
            
            reviewers = [r['login'] for r in result['users']]
            teams = [t['name'] for t in result['teams']]
            
            return [types.TextContent(
                type="text",
                text=f"👥 Reviewer'lar eklendi!\n\n"
                     f"**PR #:** {pr_number}\n"
                     f"**Kullanıcılar:** {', '.join(reviewers) if reviewers else 'Yok'}\n"
                     f"**Takımlar:** {', '.join(teams) if teams else 'Yok'}"
            )]
        
        elif name == "get_pr_files":
            owner, repo = await parse_repo_url(arguments["repo_url"])
            pr_number = arguments["pr_number"]
            
            result = await github_request(
                "GET",
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
            )
            
            files_summary = []
            for file in result:
                status_emoji = {
                    "added": "➕",
                    "modified": "📝",
                    "removed": "➖",
                    "renamed": "📋"
                }.get(file['status'], "❓")
                
                files_summary.append(
                    f"{status_emoji} {file['filename']} "
                    f"(+{file['additions']}/-{file['deletions']})"
                )
            
            return [types.TextContent(
                type="text",
                text=f"📁 Pull Request #{pr_number} Dosya Değişiklikleri:\n\n" +
                     "\n".join(files_summary) +
                     f"\n\n**Toplam:** {len(result)} dosya değişti"
            )]
        
        else:
            raise ValueError(f"Bilinmeyen tool: {name}")
    
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"❌ Hata: {str(e)}"
        )]

# Ana fonksiyon
async def main():
    # Sunucuyu stdio üzerinden çalıştır
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="github-pr-server",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# Cleanup
async def cleanup():
    await http_client.aclose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(cleanup())