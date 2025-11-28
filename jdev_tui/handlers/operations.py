"""
Operations Command Handler.

Handles: /pr, /pr-draft, /image, /pdf, /audit, /diff, /backup,
         /restore, /undo, /redo, /undo-stack, /secrets, /secrets-staged
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jdev_tui.app import QwenApp
    from jdev_tui.widgets.response_view import ResponseView


class OperationsHandler:
    """Handler for operations commands."""

    def __init__(self, app: "QwenApp"):
        self.app = app

    @property
    def bridge(self):
        return self.app.bridge

    async def handle(
        self,
        command: str,
        args: str,
        view: "ResponseView"
    ) -> None:
        """Route to specific handler method."""
        handlers = {
            "/pr": self._handle_pr,
            "/pr-draft": self._handle_pr_draft,
            "/image": self._handle_image,
            "/pdf": self._handle_pdf,
            "/audit": self._handle_audit,
            "/diff": self._handle_diff,
            "/backup": self._handle_backup,
            "/restore": self._handle_restore,
            "/undo": self._handle_undo,
            "/redo": self._handle_redo,
            "/undo-stack": self._handle_undo_stack,
            "/secrets": self._handle_secrets,
            "/secrets-staged": self._handle_secrets_staged,
        }

        handler = handlers.get(command)
        if handler:
            await handler(args, view)

    async def _handle_pr(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## 🔀 Create Pull Request\n\n"
                "**Usage:** `/pr <title>`\n\n"
                "**Options:**\n"
                "- `/pr <title>` - Create PR with title\n"
                "- `/pr-draft <title>` - Create draft PR\n\n"
                "**Requirements:**\n"
                "- GitHub CLI (gh) installed\n"
                "- Authenticated with `gh auth login`\n"
                "- Changes committed and pushed"
            )
        else:
            try:
                view.add_system_message("🔄 Creating pull request...")
                result = await self.bridge.create_pull_request(title=args)
                if result.get("success"):
                    view.add_system_message(
                        f"## ✅ Pull Request Created!\n\n"
                        f"**URL:** {result.get('url')}\n"
                        f"**Branch:** {result.get('branch')} → {result.get('base')}"
                    )
                else:
                    view.add_error(f"PR creation failed: {result.get('error')}")
            except Exception as e:
                view.add_error(f"PR error: {e}")

    async def _handle_pr_draft(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/pr-draft <title>`")
        else:
            try:
                view.add_system_message("🔄 Creating draft pull request...")
                result = await self.bridge.create_pull_request(title=args, draft=True)
                if result.get("success"):
                    view.add_system_message(
                        f"## ✅ Draft PR Created!\n\n"
                        f"**URL:** {result.get('url')}\n"
                        f"**Branch:** {result.get('branch')} → {result.get('base')}\n"
                        f"**Status:** Draft"
                    )
                else:
                    view.add_error(f"PR creation failed: {result.get('error')}")
            except Exception as e:
                view.add_error(f"PR error: {e}")

    async def _handle_image(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## 🖼️ Image Reading\n\n"
                "**Usage:** `/image <path>`\n\n"
                "Reads an image and makes it available for AI analysis.\n"
                "Supports: PNG, JPEG, GIF, WebP\n\n"
                "*Note: Install Pillow for automatic resizing: `pip install Pillow`*"
            )
        else:
            result = self.bridge.read_image(args)
            if result.get("success"):
                size_info = ""
                if result.get("resized"):
                    size_info = f" (resized from {result.get('original_size')} to {result.get('final_size')})"
                view.add_system_message(
                    f"## 🖼️ Image Loaded\n\n"
                    f"**File:** `{result.get('file')}`\n"
                    f"**Type:** {result.get('mime_type')}{size_info}\n\n"
                    f"Image data is ready for AI analysis."
                )
                # Store for next AI request
                self.app._pending_image = result
            else:
                view.add_error(result.get("error", "Failed to read image"))

    async def _handle_pdf(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_system_message(
                "## 📄 PDF Reading\n\n"
                "**Usage:** `/pdf <path>`\n\n"
                "Extracts text from PDF for AI analysis.\n\n"
                "*Note: Install PyMuPDF or pypdf: `pip install PyMuPDF`*"
            )
        else:
            result = self.bridge.read_pdf(args)
            if result.get("success"):
                pages = result.get("pages", [])
                preview = pages[0]["text"][:300] if pages else "No text extracted"
                view.add_system_message(
                    f"## 📄 PDF Loaded\n\n"
                    f"**File:** `{result.get('file')}`\n"
                    f"**Pages:** {result.get('total_pages')}\n"
                    f"**Extractor:** {result.get('extractor')}\n\n"
                    f"**Preview:**\n```\n{preview}...\n```"
                )
                # Store for next AI request
                self.app._pending_pdf = result
            else:
                view.add_error(result.get("error", "Failed to read PDF"))

    async def _handle_audit(self, args: str, view: "ResponseView") -> None:
        if not args:
            result = self.bridge.get_audit_log(limit=20)
            if result.get("success"):
                entries = result.get("entries", [])
                lines = [f"## 📋 Audit Log ({result.get('total', 0)} total)\n"]
                if entries:
                    for e in entries[:15]:
                        ts = e.get("timestamp", "")[:19]
                        action = e.get("action", "?")
                        result_status = e.get("result", "")
                        lines.append(f"- `{ts}` **{action}** [{result_status}]")
                else:
                    lines.append("*No audit entries yet*")
                lines.append(f"\n**Log file:** `{result.get('file')}`")
                view.add_system_message("\n".join(lines))
            else:
                view.add_error(result.get("error"))
        elif args == "clear":
            log_file = self.bridge._get_audit_log_file()
            if log_file.exists():
                log_file.unlink()
                view.add_system_message("Audit log cleared.")
            else:
                view.add_system_message("No audit log to clear.")
        elif args in ("on", "enable"):
            self.bridge.set_audit_enabled(True)
            view.add_system_message("✅ Audit logging enabled")
        elif args in ("off", "disable"):
            self.bridge.set_audit_enabled(False)
            view.add_system_message("⏸️ Audit logging disabled")

    async def _handle_diff(self, args: str, view: "ResponseView") -> None:
        view.add_system_message(
            "## 📝 Diff Preview\n\n"
            "Use diff preview programmatically via `bridge.preview_diff(file, old, new)`\n"
            "This shows unified diff before applying edits."
        )

    async def _handle_backup(self, args: str, view: "ResponseView") -> None:
        if not args:
            result = self.bridge.list_backups(limit=20)
            if result.get("success"):
                backups = result.get("backups", [])
                lines = [f"## 💾 Backups ({result.get('total', 0)} total)\n"]
                if backups:
                    for b in backups[:15]:
                        lines.append(f"- `{b.get('timestamp')}` {b.get('original_name')} ({b.get('reason')})")
                else:
                    lines.append("*No backups yet*")
                lines.append(f"\n**Backup dir:** `{result.get('backup_dir')}`")
                view.add_system_message("\n".join(lines))
            else:
                view.add_error(result.get("error"))
        else:
            result = self.bridge.create_backup(args, reason="manual")
            if result.get("success"):
                view.add_system_message(
                    f"## 💾 Backup Created\n\n"
                    f"**Original:** `{result.get('original')}`\n"
                    f"**Backup:** `{result.get('backup')}`"
                )
            else:
                view.add_error(result.get("error"))

    async def _handle_restore(self, args: str, view: "ResponseView") -> None:
        if not args:
            view.add_error("Usage: `/restore <backup_path>` or `/restore <backup_path> <target_path>`")
        else:
            parts = args.split(maxsplit=1)
            backup_path = parts[0]
            target_path = parts[1] if len(parts) > 1 else None
            result = self.bridge.restore_backup(backup_path, target_path)
            if result.get("success"):
                view.add_system_message(
                    f"## ✅ Restored\n\n"
                    f"**From:** `{result.get('restored_from')}`\n"
                    f"**To:** `{result.get('restored_to')}`"
                )
            else:
                view.add_error(result.get("error"))

    async def _handle_undo(self, args: str, view: "ResponseView") -> None:
        result = self.bridge.undo()
        if result.get("success"):
            view.add_system_message(
                f"## ↩️ Undone\n\n"
                f"**Operation:** {result.get('undone')}\n"
                f"**File:** `{result.get('file')}`\n"
                f"**Remaining undos:** {result.get('remaining_undos')}"
            )
        else:
            view.add_error(result.get("error"))

    async def _handle_redo(self, args: str, view: "ResponseView") -> None:
        result = self.bridge.redo()
        if result.get("success"):
            view.add_system_message(
                f"## ↪️ Redone\n\n"
                f"**Operation:** {result.get('redone')}\n"
                f"**File:** `{result.get('file')}`\n"
                f"**Remaining redos:** {result.get('remaining_redos')}"
            )
        else:
            view.add_error(result.get("error"))

    async def _handle_undo_stack(self, args: str, view: "ResponseView") -> None:
        result = self.bridge.get_undo_stack()
        lines = ["## ↩️ Undo Stack\n"]
        lines.append(f"**Undo available:** {result.get('undo_count', 0)}")
        lines.append(f"**Redo available:** {result.get('redo_count', 0)}\n")

        if result.get("undo_operations"):
            lines.append("**Recent operations (undoable):**")
            for op in result.get("undo_operations", [])[:5]:
                lines.append(f"- {op.get('operation')} on `{op.get('file')}`")
        view.add_system_message("\n".join(lines))

    async def _handle_secrets(self, args: str, view: "ResponseView") -> None:
        if not args:
            args = "."

        view.add_system_message(f"🔍 Scanning `{args}` for secrets...")
        result = self.bridge.scan_secrets(args)

        if result.get("success"):
            findings = result.get("findings", [])
            severity = result.get("severity", "CLEAN")

            if severity == "CLEAN":
                view.add_system_message(
                    f"## ✅ No Secrets Found\n\n"
                    f"**Files scanned:** {result.get('files_scanned')}\n"
                    f"**Status:** CLEAN"
                )
            else:
                lines = ["## 🚨 Secrets Found!\n"]
                lines.append(f"**Findings:** {result.get('findings_count')}")
                lines.append(f"**Files scanned:** {result.get('files_scanned')}\n")

                for f in findings[:10]:
                    lines.append(f"- **{f.get('type')}** in `{f.get('file')}` line {f.get('line')}")

                if len(findings) > 10:
                    lines.append(f"\n*...and {len(findings) - 10} more*")

                view.add_system_message("\n".join(lines))
        else:
            view.add_error(result.get("error"))

    async def _handle_secrets_staged(self, args: str, view: "ResponseView") -> None:
        view.add_system_message("🔍 Scanning staged files for secrets...")
        result = self.bridge.scan_staged_secrets()

        if result.get("success"):
            if result.get("can_commit", True):
                view.add_system_message(
                    f"## ✅ Safe to Commit\n\n"
                    f"**Staged files:** {result.get('files_scanned')}\n"
                    f"**Secrets found:** 0"
                )
            else:
                findings = result.get("findings", [])
                lines = ["## 🚨 DO NOT COMMIT!\n"]
                lines.append(f"**Secrets found:** {result.get('findings_count')}\n")
                for f in findings[:5]:
                    lines.append(f"- **{f.get('type')}** in `{f.get('file')}`")
                view.add_system_message("\n".join(lines))
        else:
            view.add_error(result.get("error"))
